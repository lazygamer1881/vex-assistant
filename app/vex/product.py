"""Vex 4.0 product release: boot checks, briefing cards, media panels, task step log, theme gallery, smart-home tiles,
first-run wizard, About/changelog, idle wallpaper, mini-orb and showcase mode. Original art.
Safety: camera off unless enabled, UI sounds off unless enabled, nothing signs in, sends, buys or records."""
import os, re, time, json, threading, logging, collections, urllib.parse, urllib.request
from . import config, __version__

log = logging.getLogger("vex.product")
TAGLINE = "Your desktop, awake."
STEPS = collections.deque(maxlen=60)
SHOW = {"on": False}

CHANGELOG = [
    ("4.3.0", "Public Edition: a much smaller installer (the speech engine and AI models now download on first run from their official sources, "
              "each file checked against a pinned checksum); a new first-run setup for anyone: name your assistant, how it addresses you, mic and "
              "speaker test, voice pack download, brain choice (free local Ollama set up for you, or your own API key), theme, privacy summary and a "
              "skippable intro; a Permissions page that shows every switch and everything that always asks first; local crash reports you can "
              "open or copy in one click (personal paths blanked out, never sent); an optional update check; crash-proof startup; and an "
              "uninstaller that removes everything. Fixed: background PC alerts and 10-minute reminder heads-ups had silently stopped "
              "working (a settings lookup error); the new crash reports caught it."),
    ("4.2.0", "Smarter, faster assistant: answers are spoken sentence by sentence while they're still being written; auto mic level, room-noise calibration "
              "and a soft noise gate for USB mics; the mic reconnects by itself if it drops or is replugged; sound-alike app matching for 'bring up'; "
              "older memories come back when they match what you ask; quick timers with labels and countdown chips, faster reminders; "
              "a 'what can you do' help card; a mic status dot on the HUD (level only, nothing recorded). Speed: a small fast model stays loaded for quick chat and the big one is used only for hard questions; shorter prompts; common commands answered instantly without the AI; faster speech recognition with voice detection; common phrases pre-voiced and speech generated in parallel. Typical reply now starts in about 2-3 s instead of ~1 minute. Dashboard tabs fixed: Home, System (gauges, top processes, drives, network), Activity (timeline) and Memory (search, add, delete) each have their own layout, with a clear active-tab bar and a smooth switch; works by mouse, hand swipe or voice ('show system tab')."),
    ("4.1.0", "New startup presentation: cinematic letterbox, particle assembly of the core with a camera fly-through and depth of field, rings locking in with flash hits, "
              "'VEX // SYSTEMS ONLINE' title card, kinetic briefing, fast-cut mode tour with a unique transition per mode, holographic scan across both monitors in sync, "
              "and a shockwave back to the AI-only core. ~52 s, no sounds, skippable."),
    ("4.0.0", "Product release: cinematic boot, startup intro presentation, briefing cards, subtle captions of Vex's replies, 'show me' glass panels, task step log, "
              "mini-orb, theme gallery, idle wallpaper, smart-home tiles (opt-in), setup wizard, About page, brand kit, Setup.exe, showcase mode. "
              "Core colour now follows every mode."),
    ("3.9.0", "Blueprint companion HUD on every other monitor; per-mode aesthetics."),
    ("3.8.0", "Abstract AI entity core (no face), blueprint layout, UI sounds off by default, more natural voice."),
    ("3.7.1", "Humanlike voice: contractions, warmer phrasing, natural pauses."),
    ("3.7.0", "Reactor HUD in the expanded view."),
    ("3.6.0", "Cinematic visuals: bloom, chromatic aberration, grain."),
    ("3.5.0", "Colour purpose modes: Assistant, Combat, Study, Creator, Business, Chill, Diagnostics, Stealth."),
    ("3.4.0", "Diagnostics scan, boot greeting, holographic notification cards."),
]

THEMES = [  # named theme gallery (one per mode)
    ("blue", "Blueprint", "Navy grid, targeting ring, particle core"),
    ("red", "Strike", "Tactical hazard stripes, crosshairs, spiky fast core"),
    ("green", "Grove", "Calm organic waves, rounded panels, breathing core"),
    ("purple", "Studio", "Broadcast frames, waveform, flattened pulse core"),
    ("gold", "Ledger", "Finance terminal, ticker tape, crystal core"),
    ("pink", "Nightdrive", "Synthwave sun, slow particles, drifting cloud core"),
    ("white", "Lab", "Clean scan grid, scanline, scanning-disc core"),
    ("black", "Shade", "Near-dark, dim red text, privacy blur, small core"),
]


def _app():
    from . import displays
    return displays.APP.get("app")


def emit(ev, data):
    a = _app()
    if a:
        try: a.emit(ev, data)
        except Exception: log.exception("emit")


# ---------------- task step log
def step(text, state="run"):
    STEPS.appendleft({"t": time.strftime("%H:%M:%S"), "text": str(text)[:160], "state": state})
    emit("step", STEPS[0])


def wrap_tools():
    """Every tool call shows as a step: running -> done / failed."""
    try:
        from . import tools
        if getattr(tools.run_tool, "_v40", False): return
        orig = tools.run_tool
        def run_tool(name, args):
            step(f"{name} {json.dumps(args)[:90] if args else ''}", "run")
            try:
                r = orig(name, args); step(f"{name} finished", "ok"); return r
            except Exception as e:
                step(f"{name} failed: {e}", "err"); raise
        run_tool._v40 = True; tools.run_tool = run_tool
    except Exception:
        log.exception("wrap tools")


# ---------------- boot cinematic data
def boot_info():
    from . import assist, displays
    checks = []
    def ck(name, fn):
        try: v = fn(); checks.append({"k": name, "v": str(v)[:40], "ok": True})
        except Exception as e: checks.append({"k": name, "v": "unavailable", "ok": False})
    a = _app()
    st = getattr(getattr(a, "vex", None), "status", {}) or {}
    ck("CORE", lambda: f"VEX {__version__}")
    ck("NEURAL ENGINE", lambda: st.get("llm") or "local")
    ck("SPEECH", lambda: st.get("stt") or "ready")
    ck("VOICE", lambda: "ONLINE")
    ck("DISPLAYS", lambda: f"{len(displays.monitors())} MONITORS")
    ck("MEMORY", lambda: f"{len(assist.memories())} ITEMS")
    ck("CAMERA", lambda: "OFF" if not config.get("hand_control") else "ENABLED")
    ck("UI SOUNDS", lambda: "ON" if config.get("ui_sounds") else "OFF")
    w = {}
    try: w = (a.api._jw if a and getattr(a.api, "_jw", None) else assist.weather_data()) or {}
    except Exception: pass
    h = time.localtime().tm_hour
    part = "morning" if 5 <= h < 12 else "afternoon" if h < 18 else "evening"
    wx = f"{round(w['temp'])}° and {w.get('desc','')}" if w.get("temp") is not None else ""
    return {"name": config.get("assistant_name") or "Vex", "version": __version__, "tagline": TAGLINE, "checks": checks,
            "time": time.strftime("%I:%M %p").lstrip("0"), "part": part, "wx": wx, "user": config.get("user_name") or "sir",
            "skip": bool(config.get("boot_cinematic") is False) or bool(intro_due() and not _gaming())}


def welcome_line(b=None):
    b = b or boot_info()
    return f"Welcome back, sir. It's {b['time']}" + (f", {b['wx']} outside." if b["wx"] else ".") + " All systems are online."


# ---------------- briefing cards
def briefing_cards():
    from . import assist, modes, extras
    d = {}
    try: d = assist.briefing_data()
    except Exception: pass
    st = {}
    try: st = assist.pc_stats()
    except Exception: pass
    cpu, ram, gpu = +(st.get("cpu") or 0), +(st.get("ram") or 0), +(st.get("gpu") or 0)
    health = max(0, min(100, round(100 - 0.22 * cpu - 0.22 * ram - 0.12 * gpu - (15 if (st.get("gpu_temp") or 0) > 80 else 0))))
    w = d.get("weather") or {}
    goals = []
    try: goals = [x.get("text", str(x)) for x in modes.goals()][:3]
    except Exception: pass
    cards = [
        {"k": "weather", "title": "WEATHER", "big": f"{round(w['temp'])}°" if w.get("temp") is not None else "--",
         "sub": (w.get("desc") or "").upper(), "rows": [[x.get("day", "")[:3].upper(), f"{x.get('hi','')}° / {x.get('lo','')}°"] for x in (w.get("days") or [])[:3]]},
        {"k": "tasks", "title": "TASKS", "big": str(len(d.get("todos") or [])), "sub": "OPEN",
         "rows": [["◆", t[:28]] for t in (d.get("todos") or [])[:3]] or [["--", "Nothing on the list"]]},
        {"k": "rem", "title": "REMINDERS", "big": str(len(d.get("reminders") or [])), "sub": "TODAY",
         "rows": [[r.get("due", "")[11:16], r.get("text", "")[:28]] for r in (d.get("reminders") or [])[:3]] or [["--", "Nothing due today"]]},
        {"k": "pc", "title": "PC HEALTH", "big": f"{health}%", "sub": "SYSTEM",
         "rows": [["CPU", f"{st.get('cpu','--')}%"], ["RAM", f"{st.get('ram','--')}%"], ["GPU", f"{st.get('gpu_temp','--')}°C"]]},
        {"k": "goals", "title": "GOALS", "big": str(len(goals)), "sub": "TRACKED", "rows": [["◆", x[:30]] for x in goals] or [["--", "Say 'add goal' to track one"]]},
    ]
    if modes.current() == "black":  # stealth: hide personal info
        for c in cards:
            if c["k"] in ("rem", "goals", "weather", "tasks"): c["rows"] = [["", "hidden in stealth"]]
    return {"greeting": d.get("greeting", "Hello"), "time": d.get("time", ""), "date": d.get("date", ""), "cards": cards}


def brief(spoken=True):
    c = briefing_cards(); emit("briefing", c)
    if not spoken: return ""
    from . import assist
    try: return assist.briefing()
    except Exception: return "Here's your briefing."


# ---------------- 'show me X' glass panel
YT = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})")


def media_for(q):
    q = (q or "").strip()
    m = YT.search(q)
    if m: return {"kind": "youtube", "id": m.group(1), "title": "YouTube"}
    if re.match(r"https?://\S+\.(png|jpe?g|gif|webp)(\?\S*)?$", q, re.I): return {"kind": "image", "src": q, "title": q.rsplit("/", 1)[-1][:60]}
    if os.path.isfile(q) and q.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        import base64
        with open(q, "rb") as f: b = base64.b64encode(f.read()[:6_000_000]).decode()
        return {"kind": "image", "src": f"data:image/{q.rsplit('.',1)[-1].lower().replace('jpg','jpeg')};base64,{b}", "title": os.path.basename(q)}
    if re.match(r"https?://", q): return {"kind": "link", "url": q, "title": q[:80]}
    # topic: public Wikipedia summary + image (read-only, no account)
    try:
        u = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(q.replace(" ", "_"))
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Vex/4.0"}), timeout=6).read())
        return {"kind": "topic", "title": r.get("title", q), "text": r.get("extract", "")[:900],
                "src": (r.get("thumbnail") or {}).get("source", ""), "url": (r.get("content_urls", {}).get("desktop", {}) or {}).get("page", "")}
    except Exception:
        return {"kind": "text", "title": q.title(), "text": "I couldn't find a picture of that, sir."}


def show_me(q):
    step(f"show me: {q}", "run")
    m = media_for(q); emit("media", m); step(f"panel: {m.get('title')}", "ok")
    return m


# ---------------- smart home tiles (opt-in, disconnected by default)
def smart_tiles():
    sh = config.get("smart_home") or {}
    out = []
    for k, name in (("ha", "Home Assistant"), ("govee", "Govee"), ("kasa", "TP-Link Kasa"), ("hue", "Philips Hue")):
        connected = bool((sh.get(k) or {}).get("connected"))
        try:
            from . import smarthome
            c = smarthome.configured(); connected = connected or bool(c.get(k))
        except Exception: pass
        out.append({"k": k, "name": name, "connected": connected})
    return {"enabled": bool(sh.get("enabled")), "mode_lights": bool(sh.get("mode_lights")), "tiles": out}


MODE_LIGHT = {"blue": "blue", "red": "red", "green": "green", "purple": "purple", "gold": "orange", "pink": "pink", "white": "white", "black": None}


def mode_lights(mode):
    """Only when he has enabled smart home + 'modes change lights' and a hub is connected."""
    t = smart_tiles()
    if not (t["enabled"] and t["mode_lights"] and any(x["connected"] for x in t["tiles"])): return
    try:
        from . import smarthome
        c = MODE_LIGHT.get(mode)
        smarthome.lights(action="color", color=c) if c else smarthome.lights(action="off")
        step(f"lights → {c or 'off'} for {mode} mode", "ok")
    except Exception as e:
        log.info("mode lights: %s", e)


# ---------------- idle (for live-wallpaper mode)
def idle_seconds():
    try:
        import ctypes
        class LII(ctypes.Structure): _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        l = LII(); l.cbSize = ctypes.sizeof(LII); ctypes.windll.user32.GetLastInputInfo(ctypes.byref(l))
        return (ctypes.windll.kernel32.GetTickCount() - l.dwTime) / 1000
    except Exception:
        return 0


# ---------------- about / wizard
def about():
    return {"name": "VEX", "version": __version__, "tagline": TAGLINE, "changelog": CHANGELOG,
            "credits": ["Original art and code · MIT License", "Python (PSF) · pywebview, numpy, psutil (BSD) · Pillow (HPND)", "faster-whisper, CTranslate2, onnxruntime (MIT) · Vosk (Apache-2.0) · Whisper base.en model (MIT)", "edge-tts, pystray (LGPL-3.0, unmodified) · three.js (MIT) · MediaPipe (Apache-2.0) · Share Tech Mono (OFL)", "Ollama and AI models are separate downloads under their own licenses"],
            "safety": ["Camera off unless you enable it", "UI sounds off unless you enable them", "Asks before power actions, deletes and sends",
                       "Never signs in to your accounts", "Never starts a stream or recording unless you ask", "Your voice is never saved: speech is transcribed in memory and discarded", "Channel stats only when you ask"]}


def wizard_state():
    return {"done": bool(config.get("setup_done")), "user_name": config.get("user_name") or "", "address": config.get("address") or "sir", "weather_city": config.get("weather_city") or "",
            "mic_device": config.get("mic_device") or "", "speaker_device": config.get("speaker_device") or "",
            "assistant_name": config.get("assistant_name") or "Vex", "mode": config.get("mode") or "blue",
            "ui_sounds": bool(config.get("ui_sounds")), "hand_control": bool(config.get("hand_control")),
            "brief_on_wake": config.get("brief_on_wake") is not False,
            "intro_on": config.get("intro_on") is not False, "intro_freq": config.get("intro_freq") or "day", "wake": (config.get("wake_phrases") or ["hey vex"])[0]}


def wizard_save(d):
    allowed = {"user_name", "assistant_name", "ui_sounds", "brief_on_wake", "setup_done", "intro_on", "intro_freq", "address", "mic_device", "speaker_device", "ollama_model", "weather_city"}
    upd = {k: v for k, v in (d or {}).items() if k in allowed}
    if "assistant_name" in upd:
        n = re.sub(r"[^A-Za-z' -]", "", str(upd["assistant_name"] or "")).strip()[:20] or "Vex"
        upd["assistant_name"] = n[:1].upper() + n[1:]
        upd.update(config.apply_names(n))
    if "user_name" in upd:
        upd["user_name"] = re.sub(r"[^\w' .-]", "", str(upd["user_name"] or "")).strip()[:30]
    if "weather_city" in upd:
        upd["weather_city"] = re.sub(r"[^\w' ,.-]", "", str(upd["weather_city"] or "")).strip()[:60]
    if "address" in upd and upd["address"] not in ("sir", "maam", "name", "none"):
        upd.pop("address")
    if "mic_device" in upd and not upd["mic_device"]:
        upd["mic_device"] = None
    if "mode" in (d or {}):
        from . import modes
        k = modes.key(d["mode"])
        if k: modes.set_mode(k)
    # the camera is never switched on from the wizard; it stays off by default
    if upd:
        config.save(upd)
        config.write_ui_brand()
        try:
            if "mic_device" in upd:   # reopen the mic on the newly picked device
                a = _app(); l = a.vex.listener
                l._close()
        except Exception:
            pass
    return wizard_state()


# ---------------- public build: first-run helpers (devices, Ollama, voice answers)
def audio_devices():
    """Input/output device names (MME entries, which work on every PC)."""
    out = {"inputs": [], "outputs": []}
    try:
        import sounddevice as sd
        apis = sd.query_hostapis()
        for d in sd.query_devices():
            api = apis[d["hostapi"]]["name"]
            if "MME" not in api:
                continue
            nm = d["name"]
            if d["max_input_channels"] > 0 and nm not in out["inputs"] and "Mapper" not in nm:
                out["inputs"].append(nm)
            if d["max_output_channels"] > 0 and nm not in out["outputs"] and "Mapper" not in nm:
                out["outputs"].append(nm)
    except Exception as e:
        log.info("devices: %s", e)
    return out


def _ollama_exe():
    import shutil
    for p in (shutil.which("ollama"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
              os.path.join(config.APP_DIR, "ollama", "ollama.exe")):
        if p and os.path.exists(p):
            return p
    return None


PULL = {"model": "", "status": "", "pct": 0, "done": False, "error": ""}


def ollama_status():
    d = {"installed": bool(_ollama_exe()), "running": False, "models": [], "want": config.get("ollama_model"), "pull": PULL}
    try:
        r = json.loads(urllib.request.urlopen(config.get("ollama_url").rstrip("/") + "/api/tags", timeout=3).read())
        d["running"] = True
        d["models"] = [m.get("name", "") for m in r.get("models", []) if "embed" not in m.get("name", "")]
        if d["models"] and not any(m == d["want"] or m.split(":")[0] == str(d["want"]).split(":")[0] for m in d["models"]):
            config.save({"ollama_model": d["models"][0]}); d["want"] = d["models"][0]   # use what they already have
    except Exception:
        pass
    return d


def ollama_pull(model):
    """Downloads a model with Ollama's own registry (the user clicks the button; Ollama shows its own sizes)."""
    model = re.sub(r"[^\w.:/-]", "", str(model or ""))[:60] or config.get("ollama_model")
    if PULL.get("model") and not PULL.get("done") and not PULL.get("error"):
        return PULL
    PULL.update(model=model, status="starting", pct=0, done=False, error="")

    def run():
        try:
            if not ollama_status()["running"]:
                exe = _ollama_exe()
                if not exe:
                    PULL.update(error="Ollama isn't installed yet."); return
                import subprocess
                subprocess.Popen([exe, "serve"], creationflags=0x08000000, close_fds=True)
                time.sleep(4)
            req = urllib.request.Request(config.get("ollama_url").rstrip("/") + "/api/pull", data=json.dumps({"name": model, "stream": True}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=7200) as r:
                for line in r:
                    try: j = json.loads(line)
                    except Exception: continue
                    if j.get("error"):
                        PULL.update(error=j["error"]); return
                    st = j.get("status", "")
                    if j.get("total"):
                        PULL["pct"] = int(100 * j.get("completed", 0) / max(1, j["total"]))
                    PULL["status"] = st
                    if st == "success":
                        break
            PULL.update(done=True, pct=100, status="ready")
            config.save({"ollama_fast_model": model} if re.search(r"[13]b|:[13]b", model) else {"ollama_model": model})
        except Exception as e:
            PULL.update(error=str(e)[:200])
    threading.Thread(target=run, daemon=True).start()
    return PULL


def wizard_listen(vex, question):
    """Asks a setup question out loud and returns what was heard (transcribed in memory, never saved)."""
    try:
        l = vex.listener
        was = l.enabled
        l.enabled = False
        time.sleep(0.6)            # let the wake loop let go of the mic
        if question:
            vex.say(str(question)[:120])
        a = l.capture(6)
        l._close()
        l.enabled = was
        if a is None:
            return {"text": ""}
        t = (vex.stt.transcribe(a) or "").strip()
        t = re.sub(r"^(?:my name is|i'?m|it'?s|call me|call it|call you|name it|you can call me)\s+", "", t, flags=re.I).strip(" .!?,")
        return {"text": t[:40]}
    except Exception as e:
        log.info("wizard listen: %s", e)
        try: vex.listener.enabled = True
        except Exception: pass
        return {"text": "", "error": str(e)[:100]}


# ---------------- showcase loop (for recording a trailer; never records anything itself)
def _gaming():
    try:
        a = _app()
        if a and a.vex.brain.cpu_only: return True
    except Exception: pass
    try:
        from . import modes
        p = modes._procs()
        return any(x in p for x in ("gorilla tag.exe", "vrmonitor.exe", "vrserver.exe"))
    except Exception: return False


def preview(m):
    """Show a mode's look without saving it (intro/showcase)."""
    from . import modes
    modes.PREVIEW["m"] = m; emit("modeset", {"mode": m or modes.current()})


INTRO = {"on": False}


def intro_due():
    if not config.get("setup_done"):
        return False   # first launch: setup wizard first, the intro plays next time
    if config.get("intro_on") is False: return False
    if (config.get("intro_freq") or "day") == "every": return True
    return config.get("intro_last") != time.strftime("%Y-%m-%d")


INTRO_DUR = 52.0  # 4.1 presentation length (s)


def _intro_payload():
    from . import displays, modes
    mons = displays.monitors() or [{"n": 1, "x": 0, "y": 0, "w": 1920, "h": 1080}]
    mm = int(config.get("main_monitor") or 1)
    main = next((m for m in mons if m["n"] == mm), mons[0])
    b = boot_info(); br = briefing_cards()
    tick = []
    try:
        st = __import__("vex.assist", fromlist=["x"]).pc_stats() or {}
        tick = [f"GOALS {len(modes.goals())} TRACKED", f"CPU {st.get('cpu','--')}%", f"RAM {st.get('ram','--')}%",
                f"GPU {st.get('gpu_temp','--')}°C", f"TASKS {len(br['cards'][1].get('rows') or []) if br['cards'][1].get('big') != '0' else 0} OPEN", "LEDGER ONLINE"]
    except Exception: tick = ["LEDGER ONLINE", "GOALS · SYSTEM LEDGER"]
    return mons, main, {"on": True, "t0": int(time.time() * 1000) + 700, "dur": INTRO_DUR, "mode": modes.current(),
            "checks": [c for c in b["checks"] if c["k"] not in ("UI SOUNDS",)] + [{"k": "PRIVACY", "v": "NO VOICE SAVED", "ok": True}],
            "brief": br, "user": config.get("user_name") or "", "time": b["time"], "tick": tick,
            "span": [min(m["x"] for m in mons), max(m["x"] + m["w"] for m in mons)],
            "core": [main["x"] + main["w"] / 2, main.get("y", 0) + main["h"] * 0.47], "main": main["n"]}


def intro(force=False):
    """4.1 startup presentation (intro41.js): letterbox, particle core assembly + camera fly-through, ring lock,
    title card, briefing, fast-cut mode tour, holographic scan across all monitors, shockwave back to the AI-only core.
    Original art, no sounds, no camera, never saves a mode, never during games/VR, skippable (click / Esc / 'skip')."""
    if INTRO["on"] or (not force and not intro_due()): return
    if _gaming():
        log.info("intro skipped: game/VR running"); return
    from . import modes, displays
    if modes.current() == "red" and not force:
        log.info("intro skipped: red (combat) mode"); return
    INTRO["on"] = True; config.save({"intro_last": time.strftime("%Y-%m-%d")})
    try: config.set_view("ai")
    except Exception: pass
    mons, main, base = _intro_payload()
    log.info("intro presentation start (4.1, %.0fs, %d monitors)", INTRO_DUR, len(mons))
    emit("intro", {"on": True}); emit("intro41", dict(base, me={"x": main["x"], "y": main.get("y", 0), "w": main["w"], "h": main["h"]}, n=main["n"]))
    sent = set()
    def push_huds(payload_on=True):
        for n, w in list(displays.HUDS.items()):
            if payload_on and n in sent: continue
            m = next((x for x in mons if x["n"] == n), None)
            if not m: continue
            d = dict(base, me={"x": m["x"], "y": m.get("y", 0), "w": m["w"], "h": m["h"]}, n=n) if payload_on else {"on": False}
            try:
                r = w.evaluate_js("window.i41?window.i41(%s):0" % json.dumps(d))
                if payload_on and r: sent.add(n)
            except Exception: pass
    spoke = False
    try:
        end = base["t0"] / 1000 + INTRO_DUR
        while time.time() < end:
            if not INTRO["on"]: break
            if _gaming(): log.info("intro stopped: game/VR started"); break
            push_huds()
            if not spoke and time.time() > base["t0"] / 1000 + 15.6:
                spoke = True
                if config.get("boot_voice"):
                    a = _app()
                    try: a and threading.Thread(target=a.vex.say, args=(welcome_line(),), daemon=True).start()
                    except Exception: pass
            time.sleep(0.25)
    finally:
        stopped = INTRO["on"] is False or time.time() < base["t0"] / 1000 + INTRO_DUR - 0.5
        INTRO["on"] = False
        try: config.set_view("ai")
        except Exception: pass
        if stopped:
            emit("intro41", {"on": False}); push_huds(False)
        emit("intro", {"on": False}); emit("modeset", {"mode": modes.current()})
        log.info("intro presentation end (%s)", "stopped" if stopped else "complete")


def skip_intro():
    INTRO["on"] = False; SHOW["on"] = False
    return "Skipped."


def showcase(on=True):
    SHOW["on"] = bool(on)
    if on: threading.Thread(target=_showcase_loop, daemon=True).start()
    emit("showcase", {"on": SHOW["on"]})
    return "Showcase mode on. I'll loop the boot, a briefing, a mode switch and a scan. I'm not recording anything; start your recorder yourself. Say 'stop showcase' to end." if on else "Showcase mode off."


def _showcase_loop():
    from . import modes
    seq = ["blue", "purple", "gold", "green", "pink", "white"]
    i = 0
    while SHOW["on"]:
        try:
            emit("boot", boot_info()); time.sleep(7)
            if not SHOW["on"]: break
            emit("briefing", briefing_cards()); time.sleep(9)
            if not SHOW["on"]: break
            m = seq[i % len(seq)]; i += 1
            preview(m); time.sleep(8)
            if not SHOW["on"]: break
            emit("scanfx", {}); step("diagnostic scan (showcase)", "ok"); time.sleep(6)
        except Exception:
            log.exception("showcase"); time.sleep(3)
    preview(None)


# ---------------- voice commands
def command(base, t):
    b = base.strip(" ,.!?")
    m = re.fullmatch(r"(?:show me|show|pull up|display) (.+?)(?: on (?:the )?(?:screen|hud|panel))?", b)
    if m and not re.match(r"(?:the )?(?:connections|agents|accounts|settings|chat|memory|stats|hud|dashboard|info|theme gallery|themes|about)\b", m.group(1)) \
            and not re.fullmatch(r"(?:the |my )?(?:home|system|activity|memories)(?: tab| page| screen| view| stats| info)?|(?:the |my )?\w+ tab|(?:the |my )?(?:permissions|privacy settings|permissions page|crash report)", m.group(1)):
        q = m.group(1)
        threading.Thread(target=show_me, args=(q,), daemon=True).start()
        return {"say": "On the panel now."}
    if re.fullmatch(r"(?:open |show )?(?:the )?(?:theme gallery|themes|theme picker)", b):
        emit("page", {"page": "themes"}); return {"say": "Here's the theme gallery."}
    if re.fullmatch(r"(?:open |show )?(?:the )?(?:about|about vex|changelog|version)(?: page)?", b):
        emit("page", {"page": "about"}); return {"say": f"Vex {__version__}. {TAGLINE}"}
    if re.fullmatch(r"(?:show |open )(?:me )?(?:the |my )?(?:permissions|privacy settings|permissions page)", b):
        emit("page", {"page": "perms"}); return {"say": "Here are your permissions."}
    if re.fullmatch(r"(?:open |show )(?:me )?(?:the )?crash report|check for updates", b):
        emit("page", {"page": "help"}); return {"say": "Here you go."}
    if re.fullmatch(r"(?:run |open |start )?(?:the )?(?:setup|setup wizard|first run setup|onboarding)", b):
        emit("page", {"page": "wizard"}); return {"say": "Let's set you up."}
    if re.fullmatch(r"skip(?: it| that| the intro| intro| presentation)?|skip intro", b) and (INTRO["on"] or SHOW["on"]):
        return {"say": skip_intro()}
    if re.fullmatch(r"(?:play|run|show) (?:the )?(?:intro|presentation|intro presentation)", b):
        threading.Thread(target=intro, args=(True,), daemon=True).start(); return {"say": ""}
    if re.fullmatch(r"(?:start |enable |turn on )?showcase(?: mode)?(?: on)?|demo loop|trailer mode", b):
        return {"say": showcase(True)}
    if re.fullmatch(r"(?:stop|end|exit|turn off) (?:the )?(?:showcase|demo loop|trailer mode)(?: mode)?|showcase off", b):
        return {"say": showcase(False)}
    if re.fullmatch(r"(?:mini ?orb|mini mode|floating orb|shrink|go small)(?: mode)?", b):
        return {"say": mini_orb(True)}
    if re.fullmatch(r"(?:full size|exit mini(?: mode)?|close (?:the )?mini ?orb|grow|big mode)", b):
        return {"say": mini_orb(False)}
    if re.fullmatch(r"(?:play |replay |show )?(?:the )?boot(?: sequence| cinematic| animation)?", b):
        emit("boot", boot_info()); return {"say": ""}
    if re.fullmatch(r"(?:clear|hide|close) (?:the )?(?:panel|media|glass panel)", b):
        emit("media", {"kind": "close"}); return {"say": "Cleared."}
    return None


# ---------------- floating mini-orb (opt-in by command only)
MINI = {"w": None}


def mini_orb(on=True):
    try:
        import webview
        a = _app()
        if on and MINI["w"] is None:
            from . import displays
            m = displays._mon(config.get("main_monitor") or 2)
            ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "mini.html")
            MINI["w"] = webview.create_window(config.brand("Vex Mini"), ui, js_api=a.api, x=m["x"] + m["w"] - 190, y=m["y"] + m["h"] - 250, width=160, height=160,
                                              frameless=True, on_top=True, resizable=False, background_color="#01060c", focus=False)
            MINI["w"].events.closed += lambda *x: MINI.update(w=None)
            return "Mini orb on. Click it to talk, double-click to bring me back."
        if not on and MINI["w"] is not None:
            w = MINI["w"]; MINI["w"] = None; w.destroy()
            try: a.show()
            except Exception: pass
            return "Back to full size."
        return "Already done."
    except Exception as e:
        log.exception("mini orb"); return "I couldn't open the mini orb."
