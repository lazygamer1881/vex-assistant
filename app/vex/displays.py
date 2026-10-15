"""Vex 3.2 multi-monitor: orb/AI window on the main monitor, optional HUD window (clock, stats, activity) on the other.
The HUD is transparent, click-through by default, never topmost, and hides in game mode."""
import os, ctypes, threading, time, logging
from ctypes import wintypes
from . import config

log = logging.getLogger("vex.displays")
APP = {"app": None, "hud": None}
IS_WIN = os.name == "nt"


def monitors():
    """[{n, x, y, w, h, primary}] left to right, 1-based n."""
    if not IS_WIN:
        return [{"n": 1, "x": 0, "y": 0, "w": 1920, "h": 1080, "primary": True}]
    class MI(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
    out = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    def cb(h, dc, r, lp):
        mi = MI(); mi.cbSize = ctypes.sizeof(MI); ctypes.windll.user32.GetMonitorInfoW(h, ctypes.byref(mi))
        rc = mi.rcMonitor; out.append({"x": rc.left, "y": rc.top, "w": rc.right - rc.left, "h": rc.bottom - rc.top, "primary": bool(mi.dwFlags & 1)})
        return 1
    ctypes.windll.user32.EnumDisplayMonitors(None, None, CB(cb), 0)
    out.sort(key=lambda m: (m["x"], m["y"]))
    for i, m in enumerate(out): m["n"] = i + 1
    return out


def _mon(n):
    ms = monitors()
    return next((m for m in ms if m["n"] == n), ms[-1])


def info():
    return {"monitors": monitors(), "mode": config.get("display_mode") or "single", "main": config.get("main_monitor") or 2,
            "clickthrough": bool(config.get("hud_clickthrough")), "style": config.get("hud_style") or "compact", "hud_open": bool(HUDS)}


def place_main(n=None):
    app = APP["app"]
    if not app or not getattr(app, "window", None): return
    m = _mon(n or config.get("main_monitor") or 2); w = app.window
    fs = getattr(app, "fullscreen", False)
    try:
        if fs: w.toggle_fullscreen(); time.sleep(0.4)
        ww, hh = min(1280, m["w"] - 80), min(820, m["h"] - 80)
        w.move(m["x"] + (m["w"] - ww) // 2, m["y"] + (m["h"] - hh) // 2); time.sleep(0.3)
        if fs: w.toggle_fullscreen()
    except Exception:
        log.exception("move main")


def move_to(n):
    ms = monitors()
    if not n or n > len(ms):
        return f"I only see {len(ms)} monitor{'s' if len(ms) != 1 else ''}."
    config.save({"main_monitor": n})
    threading.Thread(target=lambda: (place_main(n), sync_hud()), daemon=True).start()
    return f"Moving to monitor {n}."


def set_mode(mode):
    if mode in ("span", "ondemand") and len(monitors()) < 2:
        return "There's only one monitor connected."
    if mode == "ondemand":
        config.save({"display_mode": "ondemand"}); dismiss()
        return "Other monitors on demand: I'll only use them briefly when I need to show you something."
    config.save({"display_mode": mode})
    threading.Thread(target=sync_hud, daemon=True).start()
    return "Blueprint companion HUD on your other monitors." if mode == "span" else "Single monitor mode. I won't use the other screen."


TEMP = {"until": 0, "msg": None, "style": None}


def show_temp(secs=20, title=None, text=None, style=None):
    """Use the other monitor briefly (stats, long answers, alerts), then hide it again."""
    if (config.get("display_mode") or "span") == "single" or _hud_monitor() is None:
        return False
    try:
        if APP["app"].vex.brain.cpu_only:
            return False  # never pop up over a game
    except Exception:
        pass
    TEMP["until"] = time.time() + secs
    TEMP["msg"] = {"title": str(title)[:120], "text": str(text)[:6000], "at": time.time()} if (title or text) else None
    TEMP["style"] = style
    threading.Thread(target=sync_hud, daemon=True).start()
    threading.Thread(target=_expire, args=(TEMP["until"],), daemon=True).start()
    return True


def _expire(until):
    time.sleep(max(0, until - time.time()) + 0.2)
    if TEMP["until"] <= time.time():
        TEMP["msg"] = None; sync_hud()


def dismiss():
    TEMP["until"] = 0; TEMP["msg"] = None
    threading.Thread(target=sync_hud, daemon=True).start()
    return "Cleared the other monitor."


def _hud_monitor():
    main = config.get("main_monitor") or 2
    others = [m for m in monitors() if m["n"] != main]
    return others[0] if others else None


def _hud_rect(m):
    """Compact HUD column in the top-right corner of that monitor (never covers the whole screen)."""
    if (TEMP.get("style") or config.get("hud_style")) == "terminal" or (TEMP.get("msg") and len(TEMP["msg"]["text"]) > 500):
        return m["x"], m["y"], m["w"], m["h"] - 48  # leave the taskbar visible
    w, h = 380, min(700, m["h"] - 120)
    return m["x"] + m["w"] - w - 24, m["y"] + 24, w, h


def set_style(style):
    config.save({"hud_style": "terminal" if style == "terminal" else "compact"})
    if HUDS:
        try:
            list(HUDS.values())[0].evaluate_js(f"window.hudStyle && hudStyle('{config.get('hud_style')}')")
        except Exception: pass
        threading.Thread(target=sync_hud, daemon=True).start()
    return "Terminal HUD on the other monitor." if style == "terminal" else "Compact HUD."


def _hwnd(title):
    return ctypes.windll.user32.FindWindowW(None, title) if IS_WIN else 0


def set_clickthrough(on):
    config.save({"hud_clickthrough": bool(on)})
    for n in list(HUDS): _apply_clickthrough(n)
    return info()


# ---------------- 3.9 blueprint companion HUDs: one opaque full-screen window per non-main monitor
HUDS = {}          # monitor n -> pywebview window
_GEOM = {}         # monitor n -> (x, y, w, h)


def _title(n):
    return f"{config.assistant()} Companion {n}"


def _others():
    main = config.get("main_monitor") or 2
    return [m for m in monitors() if m["n"] != main]


def _hidden_now():
    """Hidden in red/combat mode and while Gorilla Tag / SteamVR run (brain.cpu_only)."""
    try:
        from . import modes
        if modes.current() == "red": return True
    except Exception: pass
    try: return bool(APP["app"].vex.brain.cpu_only)
    except Exception: return False


def _apply_clickthrough(n):
    """Opaque layered window (alpha 255, fixes the old white transparent window), click-through, tool window,
    never activated, pushed to the bottom of the z-order so normal windows sit on top (live wallpaper)."""
    if not IS_WIN: return
    h = _hwnd(_title(n))
    if not h: return
    GWL_EXSTYLE, LAYERED, TRANSP, TOOL, NOACT, TOPMOST = -20, 0x80000, 0x20, 0x80, 0x08000000, 0x8
    u = ctypes.windll.user32
    st = (u.GetWindowLongW(h, GWL_EXSTYLE) | LAYERED | TOOL | NOACT) & ~TOPMOST
    st = (st | TRANSP) if (config.get("hud_clickthrough") is not False) else (st & ~TRANSP)
    u.SetWindowLongW(h, GWL_EXSTYLE, st)
    u.SetLayeredWindowAttributes(h, 0, 255, 2)
    g = _GEOM.get(n)
    if g: u.SetWindowPos(h, 1, g[0], g[1], g[2], g[3], 0x10 | 0x20)       # HWND_BOTTOM, NOACTIVATE|FRAMECHANGED
    else: u.SetWindowPos(h, 1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)


def _to_bottom():
    if not IS_WIN: return
    u = ctypes.windll.user32
    for n in list(HUDS):
        h = _hwnd(_title(n))
        if h and u.IsWindowVisible(h): u.SetWindowPos(h, 1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)


def sync_hud():
    """Open/close companion HUDs to match display_mode: span = always on every other monitor,
    ondemand = only while show_temp is active, single = never."""
    try:
        import webview
        app = APP["app"]
        mode = config.get("display_mode") or "span"
        want = mode == "span" or (mode == "ondemand" and TEMP["until"] > time.time())
        others = {m["n"]: m for m in _others()} if want else {}
        hide = _hidden_now()
        for n in list(HUDS):
            if n not in others:
                w = HUDS.pop(n); _GEOM.pop(n, None)
                try: w.destroy()
                except Exception: pass
                log.info("companion HUD closed on monitor %s", n)
        ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "bphud.html")
        for n, m in others.items():
            g = (m["x"], m["y"], m["w"], m["h"])
            if n in HUDS:
                if _GEOM.get(n) != g:
                    _GEOM[n] = g; _apply_clickthrough(n)
                continue
            _GEOM[n] = g
            w = webview.create_window(_title(n), ui, js_api=app.api, x=m["x"], y=m["y"],
                                      width=m["w"], height=m["h"], frameless=True, background_color="#04163a",
                                      focus=False, on_top=False, resizable=False, hidden=hide)
            HUDS[n] = w; APP["hud"] = w
            def _loaded(*a, n=n, m=m):
                time.sleep(0.6); _apply_clickthrough(n)
                try: HUDS[n].evaluate_js(f"window.vexMon&&vexMon({n},{m['w']},{m['h']})")
                except Exception: pass
                log.info("companion HUD open on monitor %s %sx%s@%s,%s clickthrough=%s bottom=yes", n, m["w"], m["h"], m["x"], m["y"], (config.get("hud_clickthrough") is not False))
            w.events.loaded += _loaded
            w.events.closed += lambda *a, n=n: (HUDS.pop(n, None), _GEOM.pop(n, None))
        if not HUDS: APP["hud"] = None
    except Exception:
        log.exception("hud")


def watch_game_mode():
    last = None; tick = 0
    while True:
        time.sleep(3); tick += 1
        try:
            g = _hidden_now()
            if HUDS and g != last:
                for w in list(HUDS.values()):
                    try: (w.hide() if g else w.show())
                    except Exception: pass
                log.info("companion HUD %s (red/game %s)", "hidden" if g else "shown", g)
                if not g:
                    for n in list(HUDS): _apply_clickthrough(n)
            last = g
            if not g: _to_bottom()
            if tick % 20 == 0 and (config.get("display_mode") or "span") == "span":
                sync_hud()   # monitors plugged/unplugged
        except Exception:
            pass
