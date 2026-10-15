"""Vex 2.0 general assistant tools: web, weather, memory, reminders, to-dos, files, Python sandbox, briefing."""
import os, re, json, time, uuid, html, zipfile, datetime, logging, threading, subprocess, urllib.request, urllib.parse
from html.parser import HTMLParser
from . import config, actlog

log = logging.getLogger("vex.assist")
DATA = os.path.join(config.APP_DIR, "data")
SANDBOX = os.path.join(DATA, "sandbox")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"}
_lock = threading.RLock()
notify_cb = None  # set by core: notify_cb(title, text)


def _path(name):
    os.makedirs(DATA, exist_ok=True)
    return os.path.join(DATA, name)


def load(name, default):
    try:
        with open(_path(name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name, obj):
    with _lock:
        p = _path(name)
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
        os.replace(p + ".tmp", p)


def http_get(url, timeout=15, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(3_000_000)
        cs = r.headers.get_content_charset() or "utf-8"
        return raw.decode(cs, "replace"), r.headers.get("Content-Type", "")


# ------------------------------------------------------------ web
def web_search(query, n=6):
    """DuckDuckGo HTML results (public, no key)."""
    results = []
    try:
        body, _ = http_get("https://html.duckduckgo.com/html/", data=urllib.parse.urlencode({"q": query}).encode())
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?(?:class="result__snippet"[^>]*>(.*?)</a>)?', body, re.S):
            url = html.unescape(m.group(1))
            if "uddg=" in url:
                url = urllib.parse.unquote(re.search(r"uddg=([^&]+)", url).group(1))
            if "duckduckgo.com/y.js" in url:
                continue  # ads
            results.append({"title": _strip(m.group(2)), "url": url, "snippet": _strip(m.group(3) or "")})
            if len(results) >= n:
                break
    except Exception as e:
        log.warning("ddg: %s", e)
    if not results:
        try:
            body, _ = http_get("https://lite.duckduckgo.com/lite/", data=urllib.parse.urlencode({"q": query}).encode())
            for m in re.finditer(r"<a[^>]+href=\"(https?://[^\"]+)\"[^>]*class='result-link'>(.*?)</a>", body, re.S):
                results.append({"title": _strip(m.group(2)), "url": html.unescape(m.group(1)), "snippet": ""})
                if len(results) >= n: break
        except Exception as e:
            log.warning("ddg lite: %s", e)
    if not results:
        try:
            body, _ = http_get("https://www.bing.com/search?setlang=en&q=" + urllib.parse.quote(query))
            for m in re.finditer(r'<li class="b_algo".*?<h2[^>]*><a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>(.*?)</li>', body, re.S):
                sn = re.search(r"<p[^>]*>(.*?)</p>", m.group(3), re.S)
                results.append({"title": _strip(m.group(2)), "url": _unbing(html.unescape(m.group(1))), "snippet": _strip(sn.group(1) if sn else "").replace("Read more", "")})
                if len(results) >= n: break
        except Exception as e:
            log.warning("bing: %s", e)
    return results


def _unbing(u):
    m = re.search(r"[?&]u=a1([^&]+)", u)
    if "bing.com/ck/" in u and m:
        import base64
        try: return base64.urlsafe_b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4)).decode()
        except Exception: pass
    return u


def _strip(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside"}
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0; self.title = ""; self._t = False
    def handle_starttag(self, tag, a):
        if tag in self.SKIP: self.skip += 1
        if tag == "title": self._t = True
        if tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div"): self.out.append("\n")
    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip: self.skip -= 1
        if tag == "title": self._t = False
    def handle_data(self, d):
        if self._t: self.title += d
        elif not self.skip: self.out.append(d)


def read_webpage(url, max_chars=6000):
    if not re.match(r"https?://", url or ""):
        url = "https://" + (url or "").strip()
    host = urllib.parse.urlparse(url).hostname or ""
    if host in ("localhost",) or re.match(r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", host):
        return "I only read public websites."
    body, ctype = http_get(url)
    if "html" not in ctype and "text" not in ctype:
        return f"That page isn't text ({ctype})."
    p = _Text(); p.feed(body)
    text = re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", "".join(p.out))).strip()
    return f"TITLE: {p.title.strip()}\nURL: {url}\n\n{text[:max_chars]}"


def search_tool(query):
    r = web_search(query)
    if not r:
        return "Web search didn't return anything (maybe no internet)."
    lines = [f"{i+1}. {x['title']} - {x['url']}\n   {x['snippet']}" for i, x in enumerate(r)]
    # also read the top result so the model has real content to answer from
    try:
        lines.append("\nTOP RESULT TEXT:\n" + read_webpage(r[0]["url"], 2500))
    except Exception:
        pass
    return "SEARCH RESULTS for '" + query + "':\n" + "\n".join(lines)


def research(topic):
    r = web_search(topic, 5)
    if not r:
        return "Couldn't reach the web for research."
    parts = []
    for x in r[:3]:
        try:
            parts.append(read_webpage(x["url"], 2000))
        except Exception:
            parts.append(f"{x['title']} - {x['url']}\n{x['snippet']}")
    return "RESEARCH SOURCES (summarize these, cite the URLs):\n\n" + "\n\n---\n\n".join(parts)


# ------------------------------------------------------------ weather (Open-Meteo, no key)
WCODE = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "cloudy", 45: "foggy", 48: "foggy", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
         61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
         80: "rain showers", 81: "rain showers", 82: "heavy showers", 85: "snow showers", 86: "snow showers", 95: "thunderstorms", 96: "thunderstorms", 99: "thunderstorms"}
_wcache = {}


def _locate(city=""):
    city = (city or config.get("weather_city") or "").strip()
    if city:
        q = urllib.parse.quote(city.split(",")[0])
        body, _ = http_get(f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=en&format=json", 10)
        r = (json.loads(body).get("results") or [None])[0]
        if r:
            return r["latitude"], r["longitude"], f"{r['name']}, {r.get('admin1') or r.get('country', '')}"
    if not config.get("weather_auto_location"):
        raise ValueError("no city set: add your city in Settings (or turn on 'Guess my city' in Permissions)")
    body, _ = http_get("http://ip-api.com/json/?fields=lat,lon,city,regionName", 10)
    d = json.loads(body)
    return d["lat"], d["lon"], f"{d.get('city')}, {d.get('regionName')}"


def weather_data(city=""):
    key = (city or "").lower()
    if key in _wcache and time.time() - _wcache[key][0] < 900:
        return _wcache[key][1]
    lat, lon, name = _locate(city)
    u = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
         f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days=3&timezone=auto"
         f"&temperature_unit={'celsius' if config.get('units') == 'metric' else 'fahrenheit'}&wind_speed_unit={'kmh' if config.get('units') == 'metric' else 'mph'}")
    d = json.loads(http_get(u, 10)[0])
    c, dl = d["current"], d["daily"]
    out = {"place": name, "temp": round(c["temperature_2m"]), "feels": round(c["apparent_temperature"]), "desc": WCODE.get(c["weather_code"], "?"),
           "wind": round(c["wind_speed_10m"]), "unit": "°C" if config.get("units") == "metric" else "°F",
           "days": [{"date": dl["time"][i], "hi": round(dl["temperature_2m_max"][i]), "lo": round(dl["temperature_2m_min"][i]),
                     "desc": WCODE.get(dl["weather_code"][i], "?"), "rain": dl["precipitation_probability_max"][i]} for i in range(len(dl["time"]))]}
    _wcache[key] = (time.time(), out)
    return out


def weather(city=""):
    try:
        w = weather_data(city)
    except Exception as e:
        return f"Couldn't get the weather ({e})."
    t = w["days"][0]
    return (f"{w['place']}: {w['temp']}{w['unit']} and {w['desc']} (feels like {w['feels']}). Today high {t['hi']}, low {t['lo']}, "
            f"{t['rain']}% chance of rain. Tomorrow: {w['days'][1]['desc']}, high {w['days'][1]['hi']}.")


# ------------------------------------------------------------ memory
def memories():
    return load("memory.json", [])


def remember(fact):
    fact = (fact or "").strip()
    if not fact:
        return "What should I remember?"
    m = memories()
    if any(x["text"].lower() == fact.lower() for x in m):
        return "I already remember that."
    m.append({"id": uuid.uuid4().hex[:8], "text": fact[:300], "at": datetime.datetime.now().isoformat(timespec="minutes")})
    save("memory.json", m)
    actlog.write("INFO", "memory saved", None, fact[:100])
    return f"Got it, I'll remember: {fact}"


def forget(what):
    m = memories(); w = (what or "").lower().strip()
    keep = [x for x in m if not (w and (w in x["text"].lower() or x["id"] == w))]
    if len(keep) == len(m):
        return "I don't have anything like that saved."
    save("memory.json", keep)
    return f"Forgot {len(m) - len(keep)} thing(s)."


def memory_prompt(text=None):
    m = memories()
    if not m:
        return ""
    recent = [x["text"] for x in m[-30:]]
    rel = [t for t in (relevant_memories(text, 6) if text else []) if t not in recent]
    out = "Things you remember about the user (use when relevant):\n" + "\n".join("- " + t for t in recent)
    if rel:
        out += "\nOlder memories that match this question:\n" + "\n".join("- " + t for t in rel)
    return out


_STOP = set("a an the is are was were my me i you your of to in on for and or it that this do does did what whats about with at be have has".split())


def _toks(x):
    return {w[:-1] if len(w) > 4 and w.endswith("s") else w for w in re.findall(r"[a-z0-9']+", (x or "").lower()) if w not in _STOP and len(w) > 1}


def relevant_memories(text, k=6):
    """Vex 4.2: memories ranked by word overlap (+ fuzzy) with what he just said, so older facts still come back."""
    m = memories(); q = _toks(text)
    if not m or not q:
        return []
    import difflib
    out = []
    for i, x in enumerate(m):
        t = _toks(x["text"])
        if not t:
            continue
        hit = len(q & t)
        fz = sum(1 for a in q for b in t if a != b and len(a) > 3 and difflib.SequenceMatcher(None, a, b).ratio() > 0.84)
        sc = hit + 0.6 * fz
        if sc > 0:
            out.append((sc + i * 1e-4, x["text"]))
    out.sort(reverse=True)
    return [t for _, t in out[:k]]


def recall_about(topic):
    """Spoken answer for 'what do you remember about X' / 'do you remember my X'."""
    topic = (topic or "").strip(" ?.!")
    if re.fullmatch(r"(?:me|myself|anything|everything|stuff|)", topic):
        m = memories()
        if not m:
            return "Nothing saved yet. Say 'remember' and a fact, and I'll keep it."
        last = [x["text"] for x in m[-4:]]
        return f"I've got {len(m)} things saved. Most recent: " + "; ".join(last) + "."
    r = relevant_memories(topic, 3)
    if not r:
        return f"I don't have anything saved about {topic}."
    return "Here's what I remember: " + "; ".join(r) + "."


# ------------------------------------------------------------ to-dos
def todos():
    return load("todos.json", [])


def add_todo(task):
    t = todos(); t.append({"id": uuid.uuid4().hex[:8], "text": task.strip()[:200], "done": False}); save("todos.json", t)
    return f"Added to your to-do list: {task}"


def list_todos():
    t = [x for x in todos() if not x["done"]]
    return ("To-do: " + "; ".join(x["text"] for x in t)) if t else "Your to-do list is empty."


def complete_todo(task):
    t = todos(); w = task.lower()
    for x in t:
        if not x["done"] and w in x["text"].lower():
            x["done"] = True; save("todos.json", t); return f"Checked off: {x['text']}"
    return "Couldn't find that on your list."


# ------------------------------------------------------------ reminders / timers
def reminders():
    return load("reminders.json", [])


_NUMW = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45, "fifty": 50, "sixty": 60, "ninety": 90}


def words_to_num(s):
    """'half an hour' -> '30 minutes', 'an hour and a half' -> '90 minutes', 'twenty five minutes' -> '25 minutes'."""
    s = (s or "").lower()
    s = re.sub(r"\bhalf (?:an|a) hour\b", "30 minutes", s)
    s = re.sub(r"\b(?:an|a|one) hour and a half\b", "90 minutes", s)
    s = re.sub(r"\bquarter of an hour\b|\ba quarter hour\b", "15 minutes", s)
    s = re.sub(r"\b(\d+) and a half (hour|minute)s?\b", lambda m: f"{float(m.group(1)) + 0.5} {m.group(2)}s", s)
    s = re.sub(r"\b(twenty|thirty|forty|fifty)[ -](one|two|three|four|five|six|seven|eight|nine)\b", lambda m: str(_NUMW[m.group(1)] + _NUMW[m.group(2)]), s)
    s = re.sub(r"\b(" + "|".join(sorted(_NUMW, key=len, reverse=True)) + r")\b(?=\s*(?:-\s*)?(?:s|sec|secs|seconds?|m|min|mins|minutes?|h|hrs?|hours?|days?)\b)",
               lambda m: str(_NUMW[m.group(1)]), s)
    return re.sub(r"(\d)\s*-\s*(minute|second|hour)", r"\1 \2", s)


def _dur_words(sec):
    sec = int(round(sec)); h, r = divmod(sec, 3600); m, s2 = divmod(r, 60)
    p = []
    if h: p.append(f"{h} hour{'s' if h != 1 else ''}")
    if m: p.append(f"{m} minute{'s' if m != 1 else ''}")
    if s2 and not h: p.append(f"{s2} second{'s' if s2 != 1 else ''}")
    return " ".join(p) or "a moment"


def set_timer(dur, label=""):
    """Vex 4.2: 'set a 10 minute pizza timer' -> a reminder with kind=timer (shows a countdown chip on the HUD)."""
    d = words_to_num(dur)
    if not re.search(r"\d", d):
        return None
    dt = _parse_when("in " + d)
    if not dt:
        return None
    sec = (dt - datetime.datetime.now()).total_seconds()
    label = re.sub(r"^(?:the |my |a )", "", (label or "").strip(" .,"))
    r = reminders()
    r.append({"id": uuid.uuid4().hex[:8], "text": (label.capitalize() + " timer is up" if label else "Timer's up"), "due": dt.isoformat(timespec="seconds"),
              "done": False, "kind": "timer", "label": label, "set": datetime.datetime.now().isoformat(timespec="seconds")})
    save("reminders.json", r)
    return f"{(label.capitalize() + ' timer') if label else 'Timer'} set for {_dur_words(sec)}."


def active_timers():
    now = datetime.datetime.now(); out = []
    for x in reminders():
        if x.get("done"): continue
        due = datetime.datetime.fromisoformat(x["due"])
        out.append({"id": x["id"], "label": x.get("label") or ("Timer" if x.get("kind") == "timer" else x["text"]), "kind": x.get("kind", "reminder"),
                    "left": max(0, int((due - now).total_seconds())), "due": due.strftime("%I:%M %p").lstrip("0"),
                    "total": int((due - datetime.datetime.fromisoformat(x["set"])).total_seconds()) if x.get("set") else 0})
    out.sort(key=lambda z: z["left"])
    return out


def timers_left(label=""):
    t = [x for x in active_timers() if x["kind"] == "timer"]
    if label and label not in ("my", "the"):
        t = [x for x in t if label in x["label"].lower()] or t
    if not t:
        r = [x for x in active_timers() if x["kind"] != "timer"][:1]
        return "No timers running." + (f" Next reminder: {r[0]['label']} at {r[0]['due']}." if r else "")
    return " ".join(f"{('The ' + x['label'] + ' timer') if x['label'] != 'Timer' else 'Your timer'} has {_dur_words(x['left'])} left." for x in t[:3])


def cancel_timers(which=""):
    r = reminders(); w = (which or "").strip().lower(); n = 0
    live = [x for x in r if not x["done"] and x.get("kind") == "timer"]
    if w and w not in ("all", "the", "my"):
        live = [x for x in live if w in (x.get("label") or "").lower()] or live[-1:]
    for x in live:
        x["done"] = True; n += 1
    save("reminders.json", r)
    return ("Timer cancelled." if n == 1 else f"Cancelled {n} timers.") if n else "No timers running."


def _parse_when(when):
    """'in 10 minutes', '10m', '5:30 pm', 'tomorrow 8am', ISO -> datetime."""
    s = words_to_num((when or "").lower().strip())
    now = datetime.datetime.now()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\b", s)
    if m and ("in " in s or re.fullmatch(r"[\d.]+\s*\w+", s) or "from now" in s or "timer" in s):
        n, u = float(m.group(1)), m.group(2)[0]
        return now + datetime.timedelta(seconds=n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[u])
    try:
        return datetime.datetime.fromisoformat(s.upper().replace(" ", "T") if re.match(r"\d{4}-", s) else s)
    except Exception:
        pass
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", s)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").replace(".", "")
        if ap == "pm" and h < 12: h += 12
        if ap == "am" and h == 12: h = 0
        if h > 23 or mi > 59: return None
        dt = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if "tomorrow" in s: dt += datetime.timedelta(days=1)
        elif dt <= now:
            dt += datetime.timedelta(hours=12) if (not ap and h < 12 and dt + datetime.timedelta(hours=12) > now) else datetime.timedelta(days=1)
        return dt
    return None


def set_reminder(text, when):
    dt = _parse_when(when)
    if not dt:
        return "I couldn't tell when. Try 'in 10 minutes' or '5:30 pm'."
    r = reminders()
    r.append({"id": uuid.uuid4().hex[:8], "text": (text or "Timer's up").strip()[:200], "due": dt.isoformat(timespec="seconds"), "done": False})
    save("reminders.json", r)
    return f"Very good. I'll remind you to {text} at {dt.strftime('%I:%M %p').lstrip('0')}" + ("" if dt.date() == datetime.date.today() else dt.strftime(" on %a %b %d")) + "."


def list_reminders():
    r = [x for x in reminders() if not x["done"]]
    if not r: return "No reminders set."
    def when(d):
        d = datetime.datetime.fromisoformat(d); today = datetime.date.today()
        day = "today" if d.date() == today else "tomorrow" if d.date() == today + datetime.timedelta(days=1) else d.strftime("%A")
        return f"{day} at {d.strftime('%I:%M %p').lstrip('0')}"
    r = sorted(r, key=lambda x: x["due"])
    return "Reminders: " + "; ".join(f"{x.get('label') + ' timer' if x.get('kind') == 'timer' and x.get('label') else x['text']} {when(x['due'])}" for x in r[:6]) + "."


def cancel_reminder(what):
    r = reminders(); w = (what or "").lower()
    n = 0
    for x in r:
        if not x["done"] and (w in x["text"].lower() or w == x["id"] or w in ("all", "everything")):
            x["done"] = True; n += 1
    save("reminders.json", r)
    return f"Cancelled {n} reminder(s)." if n else "Couldn't find that reminder."


def reminder_loop():
    while True:
        try:
            r = reminders(); changed = False; now = datetime.datetime.now()
            for x in r:
                if not x["done"] and datetime.datetime.fromisoformat(x["due"]) <= now:
                    x["done"] = True; changed = True
                    actlog.write("INFO", "reminder", None, x["text"])
                    if notify_cb:
                        try: notify_cb("Timer" if x.get("kind") == "timer" else "Reminder", x["text"])
                        except Exception: log.exception("notify")
            if changed:
                save("reminders.json", r)
            _maybe_briefing()
        except Exception:
            log.exception("reminder loop")
        time.sleep(5)


# ------------------------------------------------------------ morning briefing (off by default)
def briefing_data():
    now = datetime.datetime.now(); h = now.hour
    hi = "Up early" if h < 5 else "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"
    d = {"greeting": f"{hi}, {config.get('user_name')}", "time": now.strftime("%I:%M %p").lstrip("0"), "date": now.strftime("%A, %B %d").replace(" 0", " "),
         "weather": None, "todos": [t["text"] for t in todos() if not t.get("done")],
         "reminders": [r for r in reminders() if not r["done"] and r["due"][:10] == now.date().isoformat()]}
    try: d["weather"] = weather_data(config.get("weather_city") or "")
    except Exception as e: log.info("briefing weather: %s", e)
    return d


def briefing():
    d = briefing_data(); butler = config.get("voice_style") == "butler"
    p = [f"{d['greeting']}. It's {d['time']} on {d['date']}."]
    w = d["weather"]
    if w:
        t = w["days"][0]
        p.append(f"In {w['place'].split(',')[0]} it's {w['temp']} degrees and {w['desc']}, heading for a high of {t['hi']} and a low of {t['lo']}"
                 + (f", with a {t['rain']} percent chance of rain." if t["rain"] and t["rain"] >= 20 else "."))
    if d["reminders"]:
        p.append("Today's reminders: " + "; ".join(f"{r['text']} at {datetime.datetime.fromisoformat(r['due']).strftime('%I:%M %p').lstrip('0')}" for r in d["reminders"][:4]) + ".")
    else:
        p.append("No reminders today.")
    n = len(d["todos"])
    p.append(f"You've {n} thing{'s' if n != 1 else ''} on the to-do list, starting with {d['todos'][0]}." if n else "Your to-do list is clear.")
    p.append("Shall I open anything for you?" if butler else "Let's get it.")
    return " ".join(p)


def _locked():
    """True if the Windows lock screen is showing (input desktop not accessible)."""
    try:
        import ctypes
        u = ctypes.windll.user32
        hd = u.OpenInputDesktop(0, False, 0x0100)
        if not hd: return True
        u.CloseDesktop(hd); return False
    except Exception:
        return False


_was_locked = [False]


def _maybe_briefing():
    now = datetime.datetime.now()
    st = load("state.json", {})
    if st.get("briefed") == now.date().isoformat() or not (4 <= now.hour < 12):
        return
    fire = False
    if config.get("briefing_on_unlock"):
        lk = _locked()
        if _was_locked[0] and not lk: fire = True
        _was_locked[0] = lk
    if config.get("morning_briefing"):
        try: hh, mm = [int(x) for x in (config.get("briefing_time") or "07:30").split(":")]
        except Exception: hh, mm = 7, 30
        if (now.hour, now.minute) >= (hh, mm): fire = True
    if fire:
        st["briefed"] = now.date().isoformat(); save("state.json", st)
        if notify_cb:
            notify_cb("Morning briefing", briefing())


# ------------------------------------------------------------ files
def _resolve_file(path):
    p = os.path.expandvars(os.path.expanduser((path or "").strip().strip('"')))
    if os.path.isfile(p):
        return p
    home = config.USERPROFILE or os.path.expanduser("~")
    for base in ("Desktop", "Documents", "Downloads", "OneDrive\\Desktop", "OneDrive\\Documents", ""):
        q = os.path.join(home, base, p)
        if os.path.isfile(q):
            return q
    # search by name in the usual folders
    name = os.path.basename(p).lower()
    for base in ("Desktop", "Documents", "Downloads", "OneDrive"):
        root = os.path.join(home, base)
        for dp, dn, fn in os.walk(root):
            if dp.count(os.sep) - root.count(os.sep) > 3:
                dn[:] = []; continue
            for f in fn:
                if name and name in f.lower():
                    return os.path.join(dp, f)
    return None


def extract_text(p):
    ext = os.path.splitext(p)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        r = PdfReader(p)
        return "\n".join((pg.extract_text() or "") for pg in r.pages[:60])
    if ext == ".docx":
        with zipfile.ZipFile(p) as z:
            x = z.read("word/document.xml").decode("utf8", "replace")
        x = re.sub(r"</w:p>", "\n", x)
        return html.unescape(re.sub(r"<[^>]+>", "", x))
    with open(p, "rb") as f:
        raw = f.read(400_000)
    return raw.decode("utf-8", "replace")


def read_file(path, max_chars=8000):
    p = _resolve_file(path)
    if not p:
        return f"I couldn't find a file called {path}."
    try:
        t = extract_text(p)
    except Exception as e:
        return f"Couldn't read {os.path.basename(p)}: {e}"
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return f"FILE {p} ({len(t)} chars){' - showing the start' if len(t) > max_chars else ''}:\n\n{t[:max_chars]}"


# ------------------------------------------------------------ python sandbox (always asks first)
def run_python(code, purpose=""):
    code = (code or "").strip()
    if not code:
        return "No code to run."
    if re.search(r"(?i)\b(telethon|twilio|smtplib|pywhatkit|yagmail|vonage|plivo|pyrogram|sendgrid|discord\.py|selenium|pyautogui|shutil\.rmtree|os\.remove|send2trash)\b", code):
        return "I won't run code that sends messages or deletes files, sir. That stays off-limits."
    def go():
        os.makedirs(SANDBOX, exist_ok=True)
        f = os.path.join(SANDBOX, f"vex_{int(time.time())}.py")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(code)
        py = os.path.join(config.APP_DIR, "python", "python.exe")
        if not os.path.exists(py):
            import sys; py = sys.executable
        try:
            r = subprocess.run([py, "-I", f], cwd=SANDBOX, capture_output=True, text=True, timeout=30,
                               creationflags=0x08000000 if os.name == "nt" else 0)
            out = (r.stdout + ("\n[stderr]\n" + r.stderr if r.stderr.strip() else ""))[-4000:]
        except subprocess.TimeoutExpired:
            out = "Stopped: took longer than 30 seconds."
        actlog.write("DONE", "run python", {"file": f}, out[:200])
        return {"say": "Ran it.", "detail": "Output:\n```\n" + (out.strip() or "(no output)") + "\n```", "tool_output": out}
    return {"say": "Want me to run this Python code? Say yes.", "confirm": go, "confirm_desc": "run Python code" + (f" ({purpose})" if purpose else ""),
            "detail": "```python\n" + code[:3000] + "\n```"}


# ------------------------------------------------------------ dashboard
def pc_stats():
    import shutil
    out = {}
    try:
        import ctypes
        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tot", ctypes.c_ulonglong), ("avail", ctypes.c_ulonglong),
                        ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong), ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
        m = MS(); m.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        out["ram"] = m.load; out["ram_total"] = round(m.tot / 2**30)
    except Exception:
        pass
    try:
        du = shutil.disk_usage("C:\\" if os.name == "nt" else "/")
        out["disk_free"] = round(du.free / 1e9); out["disk_pct"] = round(du.used / du.total * 100)
    except Exception:
        pass
    out["cpu"] = _cpu()
    out.update(_gpu())
    try:
        import psutil
        n = psutil.net_io_counters(); now = time.time(); p = _net_prev[0]
        if p:
            dt = max(0.5, now - p[0])
            out["net_down"] = round((n.bytes_recv - p[1]) / dt / 1024); out["net_up"] = round((n.bytes_sent - p[2]) / dt / 1024)
        _net_prev[0] = (now, n.bytes_recv, n.bytes_sent)
    except Exception:
        pass
    return out


_net_prev = [None]
_gpu_cache = [0, {}]


def _gpu():
    if time.time() - _gpu_cache[0] < 4:
        return _gpu_cache[1]
    out = {}
    try:
        import subprocess
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=3, creationflags=0x08000000 if os.name == "nt" else 0)
        nm, u, mu, mt, tc = [x.strip() for x in r.stdout.splitlines()[0].split(",")]
        out = {"gpu_name": nm.replace("NVIDIA GeForce ", ""), "gpu": int(u), "vram": round(int(mu) / int(mt) * 100), "gpu_temp": int(tc)}
    except Exception:
        pass
    _gpu_cache[:] = [time.time(), out]
    return out


_cpu_prev = [None]


def _cpu():
    try:
        import ctypes
        ft = ctypes.c_ulonglong
        i, k, u = ft(), ft(), ft()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
        cur = (i.value, k.value + u.value)
        p, _cpu_prev[0] = _cpu_prev[0], cur
        if not p: return None
        idle, tot = cur[0] - p[0], cur[1] - p[1]
        return round((1 - idle / tot) * 100) if tot else None
    except Exception:
        return None


def greeting():
    h = datetime.datetime.now().hour
    return ("Up late" if h < 5 else "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening") + f", {config.get('user_name')}"


# ------------------------------------------------------------ tool table
def _F(n, d, **props):
    req = [k for k, v in props.items() if not v.pop("_opt", False)]
    return {"type": "function", "function": {"name": n, "description": d, "parameters": {"type": "object", "properties": props, "required": req}}}


S = lambda d="", **k: dict({"type": "string", "description": d}, **k)
FUNCS = {
    "youtube_channel_stats": lambda: __import__("vex.extras", fromlist=["x"]).channel_stats(),
    "now_playing": lambda: __import__("vex.extras", fromlist=["x"]).now_playing(),
    "setup_status_check": lambda: __import__("vex.extras", fromlist=["x"]).status_check(),
    "web_search": lambda query: search_tool(query),
    "read_webpage": lambda url: read_webpage(url),
    "research": lambda topic: research(topic),
    "get_weather": lambda city="": weather(city),
    "remember": lambda fact: remember(fact),
    "forget": lambda what: forget(what),
    "list_memories": lambda: "\n".join("- " + x["text"] for x in memories()) or "Nothing saved yet.",
    "set_reminder": lambda text, when: set_reminder(text, when),
    "list_reminders": lambda: list_reminders(),
    "cancel_reminder": lambda what: cancel_reminder(what),
    "add_todo": lambda task: add_todo(task),
    "list_todos": lambda: list_todos(),
    "complete_todo": lambda task: complete_todo(task),
    "read_file": lambda path: read_file(path),
    "run_python": lambda code, purpose="": run_python(code, purpose),
    "morning_briefing": lambda: briefing(),
    "notify_my_phone": lambda message: __import__("vex.notify", fromlist=["x"]).push(message),
    "clean_disk": lambda: __import__("vex.pc", fromlist=["x"]).clean_disk(),
    "smart_lights": lambda action="on", room="", color="", brightness=None: __import__("vex.smarthome", fromlist=["x"]).lights(action, room, color, brightness),
}
SCHEMA = [
    _F("youtube_channel_stats", "The user's YouTube channel (handle from Settings) subscriber count, video count and latest upload views, from public data."),
    _F("now_playing", "What song or media is playing on the PC right now."),
    _F("setup_status_check", "Read-only check of which of his apps are running (Discord, OBS, Streamlabs, Steam, SteamVR, Meta Link, Gorilla Tag). Never starts streams."),
    _F("web_search", "Search the web for current info, news, facts, prices, scores, anything you're not sure about. Returns results + the top page text.", query=S()),
    _F("read_webpage", "Read the text of a public web page by URL.", url=S()),
    _F("research", "Deeper research: reads the top 3 web sources on a topic so you can summarize with citations.", topic=S()),
    _F("get_weather", "Current weather + forecast. city optional (defaults to the user's location).", city=S(_opt=True)),
    _F("remember", "Save a fact about the user to long-term memory (when they say remember/my X is...).", fact=S()),
    _F("forget", "Delete a saved memory.", what=S()),
    _F("list_memories", "List what you remember about the user."),
    _F("set_reminder", "Set a reminder or timer. when like 'in 10 minutes', '5:30 pm', 'tomorrow 8am'.", text=S(), when=S()),
    _F("list_reminders", "List upcoming reminders."),
    _F("cancel_reminder", "Cancel a reminder (or 'all').", what=S()),
    _F("add_todo", "Add a task to the to-do list.", task=S()),
    _F("list_todos", "Show the to-do list."),
    _F("complete_todo", "Mark a to-do as done.", task=S()),
    _F("read_file", "Read a txt/pdf/docx/code file on the PC (path or just its name) so you can summarize or answer questions about it.", path=S()),
    _F("run_python", "Run Python code in a sandbox folder (asks the user first). Use for math, data, testing code.", code=S(), purpose=S(_opt=True)),
    _F("morning_briefing", "Give a briefing: date, weather, to-dos, reminders."),
    _F("notify_my_phone", "Send a push notification to the user's OWN phone (his only). Use for 'text my phone', 'send me', 'remind me on my phone'. Never for other people.", message=S()),
    _F("clean_disk", "Safely free disk space: clears temp files, crash dumps, shader and browser caches (asks first). Use for any 'free up / clean my storage' request."),
    _F("smart_lights", "Control smart lights (Philips Hue / Home Assistant). action: on/off/color/brightness/dim/brighten.", action=S(), room=S(_opt=True), color=S(_opt=True), brightness=S("0-100", _opt=True)),
]
