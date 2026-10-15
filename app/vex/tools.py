"""Everything Vex can actually do on the PC. Each tool returns a short spoken reply.

Safety rules baked in here:
  * never deletes files, never buys anything, never signs in to anything
  * never starts/stops a stream or recording (only scene switching is allowed)
  * Discord: types the message but only presses Enter after the user says "send"
"""
import os, sys, time, json, glob, random, difflib, hashlib, base64, datetime, subprocess, threading, logging
import urllib.request

from . import config, winutil
from .actlog import logged, CANCEL

log = logging.getLogger("vex.tools")
DRY_RUN = False  # set by selftest: tools describe what they'd do instead of doing it

LA, PF, PF86, UP = config.LOCALAPPDATA, config.PROGRAMFILES, os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), config.USERPROFILE


def desktop_dirs():
    ds = [os.path.join(UP, "OneDrive", "Desktop"), os.path.join(UP, "Desktop"), r"C:\Users\Public\Desktop"]
    return [d for d in ds if os.path.isdir(d)]


def _first(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


# name -> how to open it and how to find its windows
def app_table():
    t = {
        "streamlabs": dict(aliases=["streamlabs", "stream labs", "streamlabs desktop", "streamlabs obs", "slobs", "my streaming app", "stream app"],
                           exe=[os.path.join(PF, "Streamlabs OBS", "Streamlabs OBS.exe"), os.path.join(PF, "Streamlabs Desktop", "Streamlabs Desktop.exe"),
                                os.path.join(LA, "Programs", "streamlabs-obs", "Streamlabs OBS.exe")],
                           match=["Streamlabs OBS", "Streamlabs Desktop", "Streamlabs"], label="Streamlabs"),
        "obs": dict(aliases=["obs", "obs studio", "o b s"], exe=[os.path.join(PF, "obs-studio", "bin", "64bit", "obs64.exe")], match=["obs64"], label="OBS"),
        "capcut": dict(aliases=["capcut", "cap cut", "my editor", "video editor"], exe=[os.path.join(LA, "CapCut", "Apps", "CapCut.exe"), os.path.join(PF, "CapCut", "CapCut.exe")],
                       match=["CapCut"], label="CapCut"),
        "steam": dict(aliases=["steam"], url="steam://open/main", match=["steam"], label="Steam"),
        "discord": dict(aliases=["discord", "this cord", "discourse"], exe=[os.path.join(LA, "Discord", "Update.exe")], args=["--processStart", "Discord.exe"],
                        match=["Discord"], label="Discord"),
        "gorilla tag": dict(aliases=["gorilla tag", "gtag", "g tag", "gorilla", "gorilla tags", "gt"], url="steam://rungameid/1533390",
                            match=["Gorilla Tag"], label="Gorilla Tag"),
        "meta link": dict(aliases=["quest link", "meta link", "link", "meta horizon", "horizon", "oculus", "meta quest link", "meta quest", "air link", "link app", "meta"],
                          exe=[os.path.join(PF, "Meta Horizon", "Support", "oculus-client", "OculusClient.exe"), os.path.join(PF, "Oculus", "Support", "oculus-client", "OculusClient.exe")],
                          match=["OculusClient", "Meta Horizon Link", "Meta Quest Link"], label="Meta Horizon Link"),
        "steamvr": dict(aliases=["steamvr", "steam vr", "vr"], url="steam://rungameid/250820", match=["vrmonitor", "SteamVR"], label="SteamVR"),
        "youtube studio": dict(aliases=["youtube studio", "studio", "yt studio", "my analytics", "analytics"], url="https://studio.youtube.com", label="YouTube Studio"),
        "my channel": dict(aliases=["my channel", "my youtube", "my youtube channel", "channel"], url=config.get("youtube_channel_url") or "https://studio.youtube.com", label="your channel"),
        "youtube": dict(aliases=["youtube", "you tube", "yt"], url="https://www.youtube.com", label="YouTube"),
        "twitch": dict(aliases=["twitch"], url=config.get("twitch_url"), label="Twitch"),
        "twitch dashboard": dict(aliases=["twitch dashboard", "twitch stream manager", "stream manager"], url="https://dashboard.twitch.tv/", label="your Twitch dashboard"),
        "chrome": dict(aliases=["chrome", "google chrome", "browser", "google", "the browser"],
                       exe=[os.path.join(PF, "Google", "Chrome", "Application", "chrome.exe"), os.path.join(PF86, "Google", "Chrome", "Application", "chrome.exe"),
                            os.path.join(LA, "Google", "Chrome", "Application", "chrome.exe")], url="https://www.google.com", match=["chrome"], label="Chrome"),
        "file explorer": dict(aliases=["file explorer", "explorer", "files", "my files"], exe=[r"C:\Windows\explorer.exe"], match=["CabinetWClass"], label="File Explorer"),
        "spotify": dict(aliases=["spotify", "music"], url="spotify:", match=["Spotify"], label="Spotify"),
    }
    for name, target in (config.get("extra_apps") or {}).items():
        key = name.lower()
        if str(target).lower().endswith(".exe"):
            t[key] = dict(aliases=[key], exe=[target], match=[os.path.splitext(os.path.basename(target))[0]], label=name)
        else:
            t[key] = dict(aliases=[key], url=target, match=[name], label=name)
    return t


FILLER = __import__("re").compile(r"\s+(?:for me|please|pls|right now|now|real quick|in \w*the?re|in it|on (?:my |the )?(?:second|2nd|other|main|first) (?:monitor|moniter|screen|display))\b.*$")


def _clean(s):
    s = FILLER.sub("", (s or "").lower().strip())
    for junk in ("the ", "my ", "up ", "app ", "please"):
        if s.startswith(junk) and s[len(junk):].strip() and junk != "my ":
            s = s[len(junk):]
    return s.strip(" .!?,")


def resolve_app(name):
    """Returns (key, info) for a spoken app name, or (None, None)."""
    n = _clean(name)
    if not n:
        return None, None
    table = app_table()
    for key, info in table.items():
        if n == key or n in info["aliases"]:
            return key, info
    for key, info in table.items():  # "open my channel please", "pull up gorilla tag"
        for a in sorted(info["aliases"], key=len, reverse=True):
            if len(a) > 3 and a in n:
                return key, info
    all_aliases = {a: k for k, i in table.items() for a in i["aliases"]}
    m = difflib.get_close_matches(n, list(all_aliases), n=1, cutoff=0.8)
    if m:
        k = all_aliases[m[0]]
        return k, table[k]
    sc = find_shortcut(n)
    if sc:
        label = os.path.splitext(os.path.basename(sc))[0]
        return label.lower(), dict(aliases=[n], shortcut=sc, match=[label], label=label)
    return None, None


def _shortcut_files():
    dirs = desktop_dirs() + [os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
                             os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs")]
    files = []
    for d in dirs:
        for ext in ("*.lnk", "*.url"):
            files += glob.glob(os.path.join(d, "**", ext), recursive=True)
    return [f for f in files if "uninstall" not in f.lower()]


def find_shortcut(name):
    n = _clean(name)
    if len(n) < 3:
        return None
    files = _shortcut_files()
    names = {os.path.splitext(os.path.basename(f))[0].lower(): f for f in files}
    if n in names:
        return names[n]
    m = difflib.get_close_matches(n, list(names), n=1, cutoff=0.75)
    if m:
        return names[m[0]]
    for k, f in names.items():
        if k.startswith(n + " ") or k == n:
            return f
    return None


def _launch(info):
    if DRY_RUN:
        return f"[dry-run] would open {info.get('label')}"
    if info.get("shortcut"):
        os.startfile(info["shortcut"])
        return None
    exe = _first(info.get("exe", []))
    if exe:
        flags = 0x00000008 if sys.platform == "win32" else 0  # DETACHED_PROCESS
        subprocess.Popen([exe] + info.get("args", []), cwd=os.path.dirname(exe), creationflags=flags, close_fds=True)
        return None
    if info.get("url"):
        os.startfile(info["url"])
        return None
    raise FileNotFoundError(info.get("label"))


OPEN_LINES = ["Opening {x}.", "Right away. {x} is opening.", "Bringing up {x}.", "{x}, coming up."]


@logged
def open_app(name):
    key, info = resolve_app(name)
    if not info:
        from . import pc
        return pc.open_anything(name)
    label = info["label"]
    if info.get("match") and not info.get("url", "").startswith("http"):
        wins = winutil.find_windows(info["match"]) if not DRY_RUN else []
        if wins and key not in ("chrome", "file explorer"):
            winutil.focus_window(wins[0]["hwnd"])
            return f"{label}'s already open, pulled it up."
    try:
        r = _launch(info)
    except FileNotFoundError:
        return f"Looks like {label} isn't installed on this PC."
    except Exception as e:
        log.exception("open failed")
        return f"Couldn't open {label}, something errored."
    return r or random.choice(OPEN_LINES).format(x=label)


def open_apps(names):
    replies = [open_app(n) for n in names]
    if len(replies) == 1:
        return replies[0]
    labels = []
    for n in names:
        k, info = resolve_app(n)
        labels.append(info["label"] if info else n)
    bad = [r for r in replies if "couldn't" in r.lower() or "isn't installed" in r.lower()]
    if bad:
        return " ".join(replies)
    return "Opening " + ", ".join(labels[:-1]) + " and " + labels[-1] + "."


def close_app(name):
    from . import pc
    key, info = resolve_app(name)
    if info and info.get("url", "").startswith("http") and not info.get("match"):
        return f"I can't close browser tabs, you gotta close {info['label']} yourself."
    return pc.window_action(name, "close")


def _window_for(name):
    key, info = resolve_app(name)
    keys = (info.get("match") or [info["label"]]) if info else [name]
    w = winutil.find_windows(keys)
    return w[0] if w else None


@logged
def snap_windows(left=None, right=None):
    wins = [w for w in winutil.list_windows() if not w["mine"]]
    if left and right:
        a, b = _window_for(left), _window_for(right)
        missing = [n for n, w in ((left, a), (right, b)) if not w]
        if missing:
            return f"I don't see {' or '.join(missing)} open."
    else:
        if len(wins) < 2:
            return "I need two windows open to split."
        a, b = wins[0], wins[1]
        if left:
            a = _window_for(left) or a
            b = next((w for w in wins if w["hwnd"] != a["hwnd"]), None)
    if a["hwnd"] == b["hwnd"]:
        return "That's the same window twice."
    if DRY_RUN:
        return f"[dry-run] would snap '{a['title']}' left and '{b['title']}' right"
    winutil.snap_pair(a["hwnd"], b["hwnd"])
    return "Done, split them side by side."


@logged
def lock_screen():
    from . import pc  # always asks first, then 30 s countdown
    return pc.power("lock")


@logged
def volume(action, steps=None):
    steps = int(steps or config.get("volume_step") or 5)
    if DRY_RUN:
        return f"[dry-run] volume {action} x{steps}"
    if action == "up":
        winutil.tap_key(winutil.VK_VOLUME_UP, steps); return "Turned it up."
    if action == "down":
        winutil.tap_key(winutil.VK_VOLUME_DOWN, steps); return "Turned it down."
    winutil.tap_key(winutil.VK_VOLUME_MUTE); return "Toggled mute."


def tell_time():
    now = datetime.datetime.now()
    return f"It's {now.strftime('%I:%M %p').lstrip('0')}."


def tell_date():
    now = datetime.datetime.now()
    return f"It's {now.strftime('%A, %B')} {now.day}."


# ---------------------------------------------------------------- Discord
_pending = {"text": None, "at": 0}


@logged
def discord_type(message):
    message = (message or "").strip().strip('"')
    if not message:
        return "What do you want me to type in Discord?"
    if DRY_RUN:
        _pending.update(text=message, at=time.time())
        return f"[dry-run] would type in Discord: {message}"
    wins = winutil.find_windows(["Discord"])
    if not wins:
        open_app("discord")
        for _ in range(30):
            time.sleep(1)
            wins = winutil.find_windows(["Discord"])
            if wins:
                time.sleep(3)
                break
    if not wins:
        return "Discord didn't open in time, try again in a sec."
    winutil.focus_window(wins[0]["hwnd"])
    fg = winutil.foreground_window()
    if not fg or "discord" not in (fg.get("exe", "") + fg.get("title", "")).lower():
        return "Couldn't get Discord in front, click into it and ask me again."
    time.sleep(0.3)
    winutil.type_text(message, cancel=CANCEL)
    _pending.update(text=message, at=time.time())
    return "Typed it in Discord. Say send to post it."


@logged
def discord_send():
    if not _pending["text"] or time.time() - _pending["at"] > 300:
        _pending.update(text=None)
        return "There's nothing waiting to send."
    if DRY_RUN:
        _pending.update(text=None)
        return "[dry-run] would press Enter in Discord"
    wins = winutil.find_windows(["Discord"])
    if not wins:
        _pending.update(text=None)
        return "Discord's closed, so I didn't send anything."
    fg = winutil.foreground_window()
    if not fg or "discord" not in (fg.get("exe", "") + fg.get("title", "")).lower():
        winutil.focus_window(wins[0]["hwnd"])
        time.sleep(0.2)
    winutil.press_enter()
    _pending.update(text=None)
    return "Sent."


@logged
def discord_cancel():
    had = bool(_pending["text"])
    _pending.update(text=None)
    return "Understood, I won't send it. It's still in the chat box if you want to delete it." if had else "Nothing to cancel."


def has_pending_discord():
    return bool(_pending["text"]) and time.time() - _pending["at"] < 300


# ---------------------------------------------------------------- trending games (public Steam data, no sign-in)
_trend_cache = {"at": 0, "items": []}
EVERGREEN = {570, 730, 578080, 440, 1172470, 252490}  # always-on-the-chart games, not "trending"


def trending_games(force=False):
    """Top sellers on Steam, games only (public store data, no sign-in)."""
    if not force and time.time() - _trend_cache["at"] < 1800 and _trend_cache["items"]:
        return _trend_cache["items"]
    import re
    req = urllib.request.Request("https://store.steampowered.com/search/results/?filter=topsellers&category1=998&json=1&cc=us&l=english",
                                 headers={"User-Agent": "Mozilla/5.0 VexAssistant"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    items, seen = [], set()
    for it in data.get("items", []):
        m = re.search(r"/apps/(\d+)/", it.get("logo", ""))
        if not m:
            continue
        appid = int(m.group(1))
        if appid in seen or appid in EVERGREEN:
            continue
        seen.add(appid)
        items.append({"id": appid, "name": it.get("name", "").replace("™", "").replace("®", "").strip()})
    _trend_cache.update(at=time.time(), items=items)
    return items


_last_suggested = {"game": None}


@logged
def trending_report(open_page=True):
    try:
        items = trending_games()
    except Exception:
        return "Couldn't reach Steam right now."
    if not items:
        return "Steam didn't give me anything right now."
    top = items[0]
    others = ", ".join(i["name"] for i in items[1:3])
    _last_suggested["game"] = top
    if open_page:
        open_store_page(top)
        return f"{top['name']} is the top seller on Steam right now, pulled up its page. {others} are up there too." if others else f"{top['name']} is the top seller on Steam right now, pulled up its page."
    return f"{top['name']} is top selling on Steam right now."


def proactive_trending_line():
    try:
        items = trending_games()
    except Exception:
        return None
    if not items:
        return None
    pick = items[0]
    _last_suggested["game"] = pick
    return f"Btw, {pick['name']} is blowing up on Steam right now. Want me to pull it up?"


@logged
def open_store_page(game=None):
    game = game or _last_suggested.get("game")
    if not game:
        return "Which game?"
    if DRY_RUN:
        return f"[dry-run] would open steam://store/{game['id']}"
    os.startfile(f"steam://store/{game['id']}")
    return f"I've pulled up {game['name']}."


@logged
def open_game_page(name):
    try:
        items = trending_games()
    except Exception:
        items = []
    names = {i["name"].lower(): i for i in items}
    m = difflib.get_close_matches(name.lower(), list(names), n=1, cutoff=0.6)
    if m:
        return open_store_page(names[m[0]])
    url = "https://store.steampowered.com/search/?term=" + urllib.request.quote(name)
    if DRY_RUN:
        return f"[dry-run] would search Steam for {name}"
    os.startfile(url)
    return f"Searched Steam for {name}."


# ---------------------------------------------------------------- stream setup + scenes
def find_stream_setup():
    p = config.get("stream_setup_shortcut")
    if p and os.path.exists(p):
        return p
    for d in desktop_dirs():
        for n in ("Start Stream.lnk", "Start Stream.url"):
            if os.path.exists(os.path.join(d, n)):
                return os.path.join(d, n)
    return None


@logged
def stream_setup():
    p = find_stream_setup()
    if not p:
        return open_apps(["streamlabs"])
    if DRY_RUN:
        return f"[dry-run] would run {p}"
    os.startfile(p)
    return "Running your Start Stream shortcut. You still hit Go Live yourself."


def go_live_refusal():
    return "I don't press Go Live, that one's on you. Hit Go Live in Streamlabs when you're ready."


class _WS:
    def __init__(self, url):
        import websocket  # websocket-client
        self.ws = websocket.create_connection(url, timeout=4)

    def send(self, obj):
        self.ws.send(json.dumps(obj))

    def recv(self):
        return json.loads(self.ws.recv())

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


STREAMLABS_ALLOWED = {"auth", "getScenes", "makeSceneActive", "activeSceneId"}


def _streamlabs_call(ws, rid, method, resource, args=None):
    assert method in STREAMLABS_ALLOWED  # never start/stop streaming or recording
    msg = {"jsonrpc": "2.0", "id": rid, "method": method, "params": {"resource": resource}}
    if args is not None:
        msg["params"]["args"] = args
    ws.send(msg)
    for _ in range(50):
        r = ws.recv()
        if r.get("id") == rid:
            if "error" in r:
                raise RuntimeError(r["error"].get("message", "error"))
            return r.get("result")
    raise TimeoutError()


def _pick_scene(names, wanted):
    w = wanted.lower().strip()
    synonyms = {"welcome": ["starting", "start", "welcome", "intro"], "starting soon": ["starting", "welcome"],
                "brb": ["brb", "be right back", "break"], "ending": ["ending", "end", "outro", "bye"], "game": ["game", "gameplay", "main", "live"],
                "just chatting": ["chat", "chatting", "camera", "cam"]}
    low = {n.lower(): n for n in names}
    if w in low:
        return low[w]
    m = difflib.get_close_matches(w, list(low), n=1, cutoff=0.6)
    if m:
        return low[m[0]]
    for key, words in synonyms.items():
        if key in w or any(x in w for x in words):
            for n in names:
                if any(x in n.lower() for x in words):
                    return n
    for n in names:
        if w in n.lower() or n.lower() in w:
            return n
    return None


@logged
def switch_scene(name):
    name = (name or "").strip() or config.get("starting_scene")
    sl_running = bool(winutil.find_windows(["Streamlabs OBS", "Streamlabs Desktop"])) if not DRY_RUN else True
    obs_running = bool(winutil.find_windows(["obs64"])) if not DRY_RUN else False
    if sl_running:
        token = config.get("streamlabs_api_token")
        if not token:
            return "I need your Streamlabs API token for scenes. It's in Streamlabs settings under Remote Control, paste it in my Settings tab."
        if DRY_RUN:
            return f"[dry-run] would switch Streamlabs scene to {name}"
        try:
            ws = _WS(f"ws://127.0.0.1:{int(config.get('streamlabs_port'))}/api/websocket")
            try:
                _streamlabs_call(ws, 1, "auth", "TcpServerService", [token])
                scenes = _streamlabs_call(ws, 2, "getScenes", "ScenesService") or []
                pick = _pick_scene([s["name"] for s in scenes], name)
                if not pick:
                    return f"No scene like {name}. You got " + ", ".join(s["name"] for s in scenes[:6]) + "."
                sid = next(s["id"] for s in scenes if s["name"] == pick)
                _streamlabs_call(ws, 3, "makeSceneActive", "ScenesService", [sid])
                return f"Switched to {pick}."
            finally:
                ws.close()
        except Exception as e:
            log.warning("streamlabs scene switch failed: %s", e)
            return "Couldn't reach Streamlabs remote control. Make sure it's on in Streamlabs settings and the token's right."
    if obs_running:
        return _obs_switch(name)
    return "Streamlabs isn't open. Say open Streamlabs first."


def _obs_switch(name):
    if DRY_RUN:
        return f"[dry-run] would switch OBS scene to {name}"
    try:
        ws = _WS(f"ws://127.0.0.1:{int(config.get('obs_websocket_port'))}")
        try:
            hello = ws.recv()["d"]
            ident = {"rpcVersion": 1}
            auth = hello.get("authentication")
            if auth:
                pw = config.get("obs_websocket_password") or ""
                secret = base64.b64encode(hashlib.sha256((pw + auth["salt"]).encode()).digest()).decode()
                ident["authentication"] = base64.b64encode(hashlib.sha256((secret + auth["challenge"]).encode()).digest()).decode()
            ws.send({"op": 1, "d": ident})
            ws.recv()
            ws.send({"op": 6, "d": {"requestType": "GetSceneList", "requestId": "1"}})
            scenes = [s["sceneName"] for s in ws.recv()["d"]["responseData"]["scenes"]]
            pick = _pick_scene(scenes, name)
            if not pick:
                return f"No OBS scene like {name}."
            ws.send({"op": 6, "d": {"requestType": "SetCurrentProgramScene", "requestId": "2", "requestData": {"sceneName": pick}}})
            ws.recv()
            return f"Switched OBS to {pick}."
        finally:
            ws.close()
    except Exception:
        return "Couldn't reach OBS websocket. Turn it on in OBS under Tools, WebSocket Server Settings."


# ---------------------------------------------------------------- tool schema for the LLM
TOOL_FUNCS = {
    "open_apps": lambda names: open_apps(names if isinstance(names, list) else [names]),
    "close_app": lambda name: close_app(name),
    "snap_windows": lambda left=None, right=None: snap_windows(left, right),
    "switch_scene": lambda scene: switch_scene(scene),
    "lock_screen": lambda: lock_screen(),
    "set_volume": lambda action, steps=None: volume(action, steps),
    "discord_type_message": lambda message: discord_type(message),
    "trending_games": lambda: trending_report(True),
    "open_steam_game_page": lambda game: open_game_page(game),
    "stream_setup": lambda: stream_setup(),
    "tell_time": lambda: tell_time(),
    "tell_date": lambda: tell_date(),
}

APP_NAMES = "streamlabs, obs, steam, discord, gorilla tag, meta link, steamvr, youtube studio, my channel, youtube, twitch, twitch dashboard, chrome, file explorer, spotify, or any desktop shortcut name"

TOOL_SCHEMA = [
    {"type": "function", "function": {"name": "open_apps", "description": "Open one or more apps or sites. Known names: " + APP_NAMES,
        "parameters": {"type": "object", "properties": {"names": {"type": "array", "items": {"type": "string"}}}, "required": ["names"]}}},
    {"type": "function", "function": {"name": "close_app", "description": "Close an app's windows (like clicking X).",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "snap_windows", "description": "Put two windows side by side. Leave both empty to split the two most recent windows.",
        "parameters": {"type": "object", "properties": {"left": {"type": "string"}, "right": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "switch_scene", "description": "Switch the Streamlabs/OBS scene (e.g. starting soon, gameplay, brb, ending). Cannot go live.",
        "parameters": {"type": "object", "properties": {"scene": {"type": "string"}}, "required": ["scene"]}}},
    {"type": "function", "function": {"name": "lock_screen", "description": "Lock the Windows PC.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "set_volume", "description": "Change PC volume.",
        "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["up", "down", "mute"]}}, "required": ["action"]}}},
    {"type": "function", "function": {"name": "discord_type_message", "description": "Type a message into Discord's open chat box (does NOT send it; user says 'send' after).",
        "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}}},
    {"type": "function", "function": {"name": "trending_games", "description": "Get what's trending/top selling on Steam and open the top game's store page.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "open_steam_game_page", "description": "Open a game's Steam store page.",
        "parameters": {"type": "object", "properties": {"game": {"type": "string"}}, "required": ["game"]}}},
    {"type": "function", "function": {"name": "stream_setup", "description": "Run the user's one-click stream setup (Link, SteamVR, Streamlabs, Gorilla Tag). Does not go live.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "tell_time", "description": "Current time.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "tell_date", "description": "Today's date.", "parameters": {"type": "object", "properties": {}}}},
]


def _pc_tools():
    from . import pc
    funcs = {
        "open_anything": lambda target: pc.open_anything(target),
        "window_action": lambda action, app="": pc.window_action(app, action),
        "show_desktop": lambda: pc.minimize_all(),
        "type_text": lambda text: pc.type_into_focused(text),
        "press_keys": lambda keys: pc.press_keys(keys),
        "mouse_click": lambda button="left", double=False, x=None, y=None, where=None: pc.mouse_click(button, bool(double), x, y, where),
        "media_control": lambda action: pc.media(action),
        "find_files": lambda name, folder=None: pc.find(name, folder),
        "open_found_file": lambda index=0: pc.open_found(int(index or 0)),
        "create_folder": lambda name, where="desktop": pc.create_folder(name, where),
        "move_item": lambda name, to: pc.move_item(name, to),
        "copy_item": lambda name, to: pc.copy_item(name, to),
        "rename_item": lambda name, new_name: pc.rename_item(name, new_name),
        "recycle_item": lambda name: pc.recycle_item(name),
        "screenshot": lambda: pc.screenshot(),
        "system_info": lambda topic: pc.system_info(topic),
        "run_powershell": lambda command, purpose="": pc.run_powershell(command, purpose),
        "power": lambda action: pc.power(action),
    }
    S = lambda **props: {"type": "object", "properties": {k: v for k, v in props.items()}, "required": [k for k, v in props.items() if not v.pop("_opt", False)]}
    st = {"type": "string"}
    schema = [
        ("open_anything", "Open any installed app, Windows setting, website, folder, or file by name.", S(target=dict(st))),
        ("window_action", "Close, minimize, maximize, restore, or focus a window. app='' means the current window.",
         S(action={"type": "string", "enum": ["close", "minimize", "maximize", "restore", "focus"]}, app=dict(st, _opt=True))),
        ("show_desktop", "Minimize everything / show the desktop.", S()),
        ("type_text", "Type text into the focused window (never presses Enter).", S(text=dict(st))),
        ("press_keys", "Press a keyboard shortcut in the focused window, e.g. 'ctrl+s', 'alt+tab', 'win+d', 'enter'.", S(keys=dict(st))),
        ("mouse_click", "Click the mouse at the cursor, at x,y, or where='center' of the current window.",
         S(button={"type": "string", "enum": ["left", "right", "middle"], "_opt": True}, double={"type": "boolean", "_opt": True},
           x={"type": "integer", "_opt": True}, y={"type": "integer", "_opt": True}, where={"type": "string", "_opt": True})),
        ("media_control", "Music/video: play or pause, next, previous, stop.", S(action={"type": "string", "enum": ["play_pause", "next", "previous", "stop"]})),
        ("find_files", "Find files or folders by name (folder can be desktop, downloads, 'd drive', 'program files', or a path).", S(name=dict(st), folder=dict(st, _opt=True))),
        ("open_found_file", "Open a result from the last find (0 = first).", S(index={"type": "integer", "_opt": True})),
        ("create_folder", "Create a folder (where = desktop, documents, downloads, or a folder name).", S(name=dict(st), where=dict(st, _opt=True))),
        ("move_item", "Move a file/folder into another folder.", S(name=dict(st), to=dict(st))),
        ("copy_item", "Copy a file/folder into another folder.", S(name=dict(st), to=dict(st))),
        ("rename_item", "Rename a file/folder.", S(name=dict(st), new_name=dict(st))),
        ("recycle_item", "Delete a file/folder by moving it to the Recycle Bin (Vex asks first).", S(name=dict(st))),
        ("screenshot", "Take a screenshot and save it to Pictures.", S()),
        ("system_info", "Check battery, disk space, ram, cpu, gpu, running apps, uptime, internet.", S(topic=dict(st))),
        ("run_powershell", "Run any PowerShell command: info, settings changes, files on any drive (read-only runs right away; anything that changes things asks the user first).",
         S(command=dict(st), purpose=dict(st, _opt=True))),
        ("power", "Shut down, restart, sign out, or sleep the PC (Vex asks first).", S(action={"type": "string", "enum": ["shutdown", "restart", "sign_out", "sleep", "lock"]})),
    ]
    return funcs, [{"type": "function", "function": {"name": n, "description": d, "parameters": p}} for n, d, p in schema]


_PC = {}


def all_tools():
    if not _PC:
        f, sch = _pc_tools()
        _PC.update(funcs={**TOOL_FUNCS, **f}, schema=TOOL_SCHEMA + sch)
    return _PC["funcs"], _PC["schema"]


def run_tool(name, args):
    fn = all_tools()[0].get(name)
    if not fn:
        return f"I can't do {name}."
    try:
        return fn(**(args or {}))
    except TypeError:
        try:
            return fn()
        except Exception:
            return "That didn't work."
    except Exception:
        log.exception("tool %s failed", name)
        return "Something went wrong with that."
