"""Vex 3.5 purpose modes. Each '<colour> mode' keeps the 3.3 cinematic and also switches Vex's job:
panels, voice line and behaviour. Safety rules are unchanged: nothing here starts a stream or recording,
kills apps, buys, sends or signs in to anything."""
import re, time, threading, logging, subprocess
from . import config

log = logging.getLogger("vex.modes")

MODES = {
    "blue":   dict(name="Assistant", color="hsl(212,100%,62%)", line="Default assistant mode. Standing by, sir.",
                   desc="Blue is the default assistant: the normal dashboard, all features, normal voice."),
    "red":    dict(name="Combat", color="hsl(355,100%,62%)", line="Combat mode engaged. Effects paused, notifications muted, GPU is yours.",
                   desc="Red is Combat, for gaming: heavy effects pause, notifications go quiet, the AI model moves to the CPU so the GPU is free, and the panel shows GPU load, temps and VRAM. Say 'launch Gorilla Tag' or 'open Steam'."),
    "green":  dict(name="Study", color="hsl(140,100%,62%)", line="Study mode. Say 'focus 25 minutes' to start a timer, or 'study' and a topic for notes.",
                   desc="Green is Study: a focus timer, notes from 'study' and a topic, tutor-style homework help that explains steps instead of just giving answers, and gentle reminders if Discord or a game opens during focus. It never closes your apps."),
    "purple": dict(name="Creator", color="hsl(272,100%,62%)", line="Creator mode. OBS and CapCut are a word away. I won't start anything unless you ask.",
                   desc="Purple is Creator: your channel stats, quick open for OBS, CapCut and YouTube Studio, and a recording checklist. Vex never starts a stream or recording unless you explicitly ask."),
    "gold":   dict(name="Business", color="hsl(45,100%,62%)", line="Business mode. Your goals and PC stats are on screen.",
                   desc="Gold is Business: channel growth since Vex started tracking, plus a goals tracker. Say 'add goal' and the goal, 'goal done' and the goal, or 'list goals'."),
    "pink":   dict(name="Chill", color="hsl(325,100%,62%)", line="Chill mode. Now playing is on screen, sir. Relax.",
                   desc="Pink is Chill: what's playing on Spotify or your media player, slow ambient visuals and a calmer orb."),
    "white":  dict(name="Diagnostics", color="#eef6ff", line="",
                   desc="White is Diagnostics: it runs a full system scan and shows the results."),
    "black":  dict(name="Stealth", color="#9fb3c2", line="Stealth mode. Lights down, voice low, personal info hidden.",
                   desc="Black, or stealth, is Night and Privacy: dim screen, quieter voice, no sound effects, notifications muted, and your name, weather, tasks and chat are hidden. Say 'goodnight' for tomorrow's rundown."),
}
ALIAS = {"stealth": "black", "night": "black", "dark": "black", "privacy": "black", "default": "blue", "normal": "blue",
         "combat": "red", "study": "green", "homework": "green", "creator": "purple",
         "recording": "purple", "business": "gold", "money": "gold", "chill": "pink", "music": "pink", "diagnostics": "white", "silver": "white"}
DISTRACT = ["discord.exe", "gorilla tag.exe", "steamvr", "vrmonitor.exe", "robloxplayerbeta.exe", "fortniteclient-win64-shipping.exe"]
FOCUS = {"end": 0, "mins": 0, "topic": "", "warned": 0}
SEQ = {"n": 0}


def key(word):
    w = (word or "").lower().strip()
    w = ALIAS.get(w, w)
    return w if w in MODES else None


PREVIEW = {"m": None}   # 4.0 intro/showcase: temporary look, never saved


def current():
    if PREVIEW["m"]: return PREVIEW["m"]
    return key(config.get("mode") or "blue") or "blue"


def set_mode(k):
    PREVIEW["m"] = None; config.save({"mode": k}); SEQ["n"] += 1; log.info("mode -> %s", k)
    try:
        from . import product; threading.Thread(target=product.mode_lights, args=(k,), daemon=True).start()
    except Exception: pass
    if k != "green": FOCUS["end"] = 0


def muted():
    return current() in ("red", "black")


def gpu_free():
    return current() == "red"


def prompt_hint():
    m = current()
    return {"green": " STUDY MODE: for homework, act as a tutor. Explain the steps and ask him to try the next step; don't just hand over final answers.",
            "purple": " CREATOR MODE: help with video ideas, titles, thumbnails and the recording checklist. Never start a stream or recording.",
            "gold": " BUSINESS MODE: focus on channel growth, goals and realistic advice. Never buy anything.",
            "red": " COMBAT MODE: he's gaming; keep replies very short.",
            "black": " STEALTH MODE: it's late; be brief and quiet."}.get(m, "")


def volume():
    return 0.45 if current() == "black" else 1.0


# ------------------------------------------------------------ goals / growth (local files only)
def goals():
    from . import assist
    return assist.load("goals.json", [])


def _save_goals(g):
    from . import assist
    assist.save("goals.json", g)


def _subs(line):
    m = re.match(r"([\d.,]+)\s*([KkMm]?)", line or "")
    if not m: return None
    n = float(m.group(1).replace(",", "")); return int(n * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1))


def growth():
    from . import assist, extras
    hist = assist.load("growth.json", [])
    line = ""
    try: line = extras.channel_cached()
    except Exception: pass
    s = _subs(line); today = time.strftime("%Y-%m-%d")
    if s is not None and (not hist or hist[-1]["d"] != today):
        hist.append({"d": today, "subs": s}); assist.save("growth.json", hist[-400:])
    elif s is not None and hist[-1]["subs"] != s:
        hist[-1]["subs"] = s; assist.save("growth.json", hist[-400:])
    first = hist[0] if hist else None
    return {"line": line, "subs": s, "since": first["d"] if first else "", "gain": (s - first["subs"]) if (first and s is not None) else None,
            "hist": hist[-30:]}


# ------------------------------------------------------------ focus timer (reminders only, never kills apps)
def _procs():
    try:
        return subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, creationflags=0x08000000, timeout=8).stdout.lower()
    except Exception:
        return ""


def start_focus(mins, say, notify):
    mins = max(1, min(180, int(mins)))
    FOCUS.update(end=time.time() + mins * 60, mins=mins, warned=0); SEQ["n"] += 1
    tok = FOCUS["end"]

    def run():
        while FOCUS["end"] == tok and time.time() < tok:
            time.sleep(20)
            if FOCUS["end"] != tok: return
            if time.time() - FOCUS["warned"] > 600:
                p = _procs(); hit = [d for d in DISTRACT if d in p]
                if hit:
                    FOCUS["warned"] = time.time()
                    notify("Focus reminder", f"{hit[0].split('.')[0].title()} is open. You've {int((tok - time.time()) / 60)} minutes of focus left.")
        if FOCUS["end"] == tok:
            FOCUS["end"] = 0; SEQ["n"] += 1
            say(f"Focus session complete, sir. {mins} minutes. Take a five minute break.")
            notify("Focus complete", f"{mins} minutes done. Break time.")
    threading.Thread(target=run, daemon=True).start()
    return f"Focus timer set for {mins} minutes. I'll nudge you if anything distracting opens, but I won't close it."


# ------------------------------------------------------------ panel data for the UI
def panel():
    m = current(); d = {"mode": m, "name": MODES[m]["name"], "color": MODES[m]["color"], "seq": SEQ["n"]}
    try:
        if m == "red":
            from . import assist
            d["stats"] = assist.pc_stats()
        elif m == "green":
            from . import study
            left = max(0, int(FOCUS["end"] - time.time())) if FOCUS["end"] else 0
            d["focus"] = {"left": left, "mins": FOCUS["mins"]}
            d["notes"] = [n.get("topic") or n.get("title") or str(n) for n in (study.notes() or [])[:5]] if hasattr(study, "notes") else []
        elif m == "purple":
            d["goals"] = goals()
        elif m == "gold":
            d["goals"] = goals()
        elif m == "pink":
            from . import extras
            d["playing"] = extras.now_playing_info()
    except Exception as e:
        log.exception("mode panel"); d["error"] = str(e)[:120]
    return d


def list_modes():
    return "Modes: " + "; ".join(f"{k} is {v['name']}" for k, v in MODES.items()) + "."


def handle(base, say, notify):
    """Mode-specific voice commands. Returns reply text or None."""
    m = re.fullmatch(r"(?:list|show|what are)(?: the| my| all| your)? (?:modes|protocols|colou?r modes)|what modes (?:are there|do you have)", base)
    if m: return list_modes()
    m = re.fullmatch(r"what (?:does|is) (?:the )?([a-z]+) (?:mode|protocol)(?: do)?", base)
    if m and key(m.group(1)): return MODES[key(m.group(1))]["desc"]
    m = re.fullmatch(r"(?:which|what) mode (?:am i|are you|are we) in", base)
    if m: c = current(); return f"{c.title()} mode, {MODES[c]['name']}."
    m = re.fullmatch(r"(?:start |begin )?(?:a )?(?:focus|study|pomodoro)(?: timer| session)?(?: for)? (\d+) ?(?:min|mins|minutes)(?: focus| timer)?|(?:start |begin )(?:a )?(?:focus|pomodoro)(?: timer| session)?|focus (\d+)(?: minutes)?", base)
    if m:
        return start_focus(next((g for g in m.groups() if g), 25), say, notify)
    if re.fullmatch(r"(?:stop|cancel|end) (?:the )?(?:focus|study|pomodoro)(?: timer| session)?", base):
        FOCUS["end"] = 0; SEQ["n"] += 1; return "Focus timer stopped."
    m = re.fullmatch(r"(?:add|set|new)(?: a| my)? goal(?: to|:)? (.+)", base)
    if m:
        g = goals(); g.append({"text": m.group(1).strip(), "done": False, "t": time.strftime("%Y-%m-%d")}); _save_goals(g); SEQ["n"] += 1
        return f"Goal added: {m.group(1).strip()}."
    m = re.fullmatch(r"(?:goal done|finished goal|complete goal|mark goal)(?: done)?:? (.+)", base)
    if m:
        g = goals(); w = m.group(1).strip()
        hit = next((x for x in g if w in x["text"].lower() and not x["done"]), None)
        if not hit: return "I couldn't find that goal."
        hit["done"] = True; _save_goals(g); SEQ["n"] += 1; return f"Marked done: {hit['text']}. Well played, sir."
    if re.fullmatch(r"(?:list|show|what are)(?: my)? goals", base):
        g = [x["text"] for x in goals() if not x["done"]]
        return ("Open goals: " + "; ".join(g) + ".") if g else "No open goals. Say 'add goal' and the goal."
    if re.fullmatch(r"(?:show |read )?(?:the )?(?:recording|record|video) checklist|checklist", base):
        return "Recording checklist: mic and game audio levels, Quest charged, OBS scene and output folder, enough disk space, notifications muted, and a hook for the first ten seconds."
    return None
