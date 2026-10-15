"""Smart home for Vex: Philips Hue (local bridge, push-link pairing) and Home Assistant (URL + token).
Safe when unconfigured: every call just explains how to set it up. Never signs in to any cloud account."""
import json, re, ssl, logging, urllib.request, urllib.error
from . import config

log = logging.getLogger("vex.smarthome")

COLORS = {"red": (0, 100), "orange": (30, 100), "yellow": (55, 100), "green": (120, 100), "cyan": (180, 100), "teal": (170, 80),
          "blue": (230, 100), "purple": (275, 100), "violet": (270, 80), "pink": (320, 70), "magenta": (300, 100), "white": (0, 0),
          "warm white": (35, 35), "warm": (35, 45), "cool white": (210, 15)}


def _req(method, url, body=None, headers=None, timeout=6):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    ctx = ssl._create_unverified_context() if url.startswith("https://") and re.match(r"https://(\d+\.|[\w-]+\.local)", url) else None
    with urllib.request.urlopen(r, timeout=timeout, context=ctx) as resp:
        t = resp.read().decode("utf-8", "replace")
        return json.loads(t) if t.strip() else {}


# ------------------------------------------------------------ Hue
def hue_discover():
    try:
        found = _req("GET", "https://discovery.meethue.com/", timeout=6)
        return [b.get("internalipaddress") for b in found if b.get("internalipaddress")]
    except Exception as e:
        log.info("hue discovery: %s", e)
        return []


def hue_pair(ip=""):
    """Push-link pairing. the user presses the round button on the bridge, then this within 30 s."""
    ip = (ip or config.get("hue_bridge_ip") or "").strip()
    if not ip:
        ips = hue_discover()
        if not ips:
            return {"ok": False, "msg": "I couldn't find a Hue bridge on your Wi-Fi. Type its IP in Settings > Smart home."}
        ip = ips[0]
    try:
        r = _req("POST", f"http://{ip}/api", {"devicetype": "vex#pc"})
    except Exception as e:
        return {"ok": False, "msg": f"Couldn't reach the bridge at {ip} ({e})."}
    item = r[0] if isinstance(r, list) and r else {}
    if "success" in item:
        config.save({"hue_bridge_ip": ip, "hue_username": item["success"]["username"]})
        return {"ok": True, "msg": f"Paired with the Hue bridge at {ip}."}
    err = (item.get("error") or {}).get("description", "unknown error")
    if "link button" in err:
        return {"ok": False, "msg": "Press the big round button on top of the Hue bridge, then click Pair again within 30 seconds."}
    return {"ok": False, "msg": "Hue said: " + err}


def _hue():
    ip, user = config.get("hue_bridge_ip"), config.get("hue_username")
    return (f"http://{ip}/api/{user}") if ip and user else None


def hue_lights():
    base = _hue()
    return _req("GET", base + "/lights") if base else {}


def _hue_targets(room):
    base = _hue(); room = (room or "").lower().strip()
    if not room or room in ("all", "the lights", "lights", "everything"):
        return [base + "/groups/0/action"]
    groups = _req("GET", base + "/groups")
    for gid, g in groups.items():
        if room in g.get("name", "").lower():
            return [f"{base}/groups/{gid}/action"]
    for lid, l in _req("GET", base + "/lights").items():
        if room in l.get("name", "").lower():
            return [f"{base}/lights/{lid}/state"]
    return []


def _hue_set(room, on=None, bri=None, color=None):
    tg = _hue_targets(room)
    if not tg:
        return f"I couldn't find a Hue room or light called {room}."
    body = {}
    if on is not None: body["on"] = on
    if bri is not None: body.update(on=True, bri=max(1, min(254, round(bri * 2.54))))
    if color:
        h, s = COLORS[color]
        body.update(on=True, hue=round(h / 360 * 65535), sat=round(s * 2.54))
    for u in tg:
        _req("PUT", u, body)
    return None


# ------------------------------------------------------------ Home Assistant
def _ha():
    url, tok = (config.get("ha_url") or "").rstrip("/"), config.get("ha_token")
    return (url, {"Authorization": "Bearer " + tok}) if url and tok else (None, None)


def ha_test():
    url, h = _ha()
    if not url:
        return {"ok": False, "msg": "Add your Home Assistant URL and a long-lived token first."}
    try:
        _req("GET", url + "/api/", headers=h)
        return {"ok": True, "msg": f"Connected to Home Assistant ({len(_ha_lights())} lights)."}
    except Exception as e:
        return {"ok": False, "msg": f"Couldn't connect ({e})."}


def _ha_lights():
    url, h = _ha()
    return [s for s in _req("GET", url + "/api/states", headers=h) if s["entity_id"].startswith("light.")]


def _ha_set(room, on=None, bri=None, color=None):
    url, h = _ha(); room = (room or "").lower().strip()
    lights = _ha_lights()
    if room and room not in ("all", "lights", "the lights", "everything"):
        lights = [l for l in lights if room in (l["attributes"].get("friendly_name", "") + " " + l["entity_id"]).lower().replace("_", " ")]
    if not lights:
        return f"I couldn't find a Home Assistant light called {room}."
    ids = [l["entity_id"] for l in lights]
    if on is False:
        _req("POST", url + "/api/services/light/turn_off", {"entity_id": ids}, h); return None
    body = {"entity_id": ids}
    if bri is not None: body["brightness_pct"] = max(1, min(100, int(bri)))
    if color:
        hh, s = COLORS[color]; body["hs_color"] = [hh, s]
    _req("POST", url + "/api/services/light/turn_on", body, h)
    return None


# ------------------------------------------------------------ public
def configured():
    return {"hue": bool(_hue()), "ha": bool(_ha()[0])}


def lights(action="on", room="", color="", brightness=None):
    """action: on / off / color / brightness / dim / brighten."""
    c = configured()
    if not (c["hue"] or c["ha"]):
        return "Smart home isn't set up yet. Open Settings > Smart home to pair a Hue bridge or add Home Assistant."
    action = (action or "on").lower(); color = (color or "").lower().strip()
    if color and color not in COLORS:
        return f"I don't know the color {color}. Try red, blue, purple, green, pink, orange, yellow or white."
    on = False if action == "off" else True if action == "on" else None
    bri = None
    if brightness not in (None, ""):
        try: bri = float(str(brightness).strip("% "))
        except ValueError: bri = None
    if action == "dim" and bri is None: bri = 25
    if action == "brighten" and bri is None: bri = 100
    errs, done = [], []
    for name, fn in (("hue", _hue_set), ("ha", _ha_set)):
        if not c[name]: continue
        try:
            e = fn(room, on=on, bri=bri, color=color or None)
            (errs if e else done).append(e or name)
        except Exception as ex:
            log.exception("lights %s", name); errs.append(f"{'Hue' if name == 'hue' else 'Home Assistant'} error: {ex}")
    if not done:
        return " ".join(errs)
    where = f" in the {room}" if room and room not in ("all", "lights", "the lights") else ""
    if on is False: return f"Lights off{where}."
    if color: return f"Lights{where} set to {color}" + (f" at {int(bri)}%." if bri else ".")
    if bri is not None: return f"Lights{where} at {int(bri)}%."
    return f"Lights on{where}."


def parse(t):
    """Voice rule: returns kwargs for lights() or None."""
    t = t.lower().strip(" .!?")
    if not re.search(r"\b(lights?|lamps?|bulbs?)\b", t):
        return None
    m = re.search(r"\b(?:in|on) the ([a-z ]+?)(?: to | at |$)|\b(?:the )?([a-z]+ ?[a-z]*) lights?\b", t)
    room = ""
    if m:
        room = (m.group(1) or m.group(2) or "").strip()
        room = re.sub(r"^(turn|switch|set|make|the|my|all|on|off|dim|brighten)\s*", "", room).strip()
        room = "" if room in ("", "the", "my", "all", "on", "off", "lights", "light", "lamp", "lamps") or room in COLORS else room
    col = next((c for c in sorted(COLORS, key=len, reverse=True) if re.search(rf"\b{c}\b", t)), "")
    b = re.search(r"(\d{1,3})\s*(?:%|percent)", t)
    if re.search(r"\b(off|kill)\b", t): act = "off"
    elif b: act = "brightness"
    elif re.search(r"\bdim\b|\bdimmer\b|\blower\b", t): act = "dim"
    elif re.search(r"\bbright(en|er)?\b|\bfull\b", t): act = "brighten"
    elif col: act = "color"
    elif re.search(r"\bon\b", t): act = "on"
    else: return None
    return {"action": act, "room": room, "color": col, "brightness": b.group(1) if b else None}
