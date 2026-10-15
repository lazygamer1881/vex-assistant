"""Vex 3.3 '<colour> protocol': cinematic recolour across every monitor, then the new theme stays (undo reverts)."""
import os, json, time, threading, logging
from . import config, look, displays

log = logging.getLogger("vex.protocol")
DUR = 7.2  # seconds, must match ui/protocol.js
_busy = threading.Lock()


def run(color, say, done=None):
    """Called after 'Very good, sir. Initiating X protocol.' was spoken."""
    pl = look.protocol_look(color)
    if not pl or not _busy.acquire(blocking=False):
        if done and pl: done()
        return
    try:
        changes, css = pl
        name = color.upper()
        app = displays.APP.get("app")
        gaming = bool(getattr(getattr(getattr(app, "vex", None), "brain", None), "cpu_only", False))
        if gaming and getattr(getattr(app, "vex", None), "game_mode", None) is not None and look.config.get("mode") == "red":
            from . import winutil  # CPU mode only because of RED mode (no real game running): keep the cinematic
            procs = winutil.running_process_names()
            gaming = any(p.lower() in procs for p in (config.get("game_mode_processes") or []))
        new = look.apply(changes, f"{color} protocol")
        if gaming or not app:
            (done() if done else say(f"{color.title()} protocol complete.")); return
        payload = json.dumps({"name": name, "color": css, "look": new})
        overlays = []
        try:
            import webview
            ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "protocol.html")
            main_n = config.get("main_monitor") or 2
            for m in ([] if (config.get("display_mode") or "ondemand") == "single" else displays.monitors()):
                if m["n"] == main_n: continue
                if m["n"] in getattr(displays, "HUDS", {}): continue  # 4.0: companion HUD already restyles itself; fewer windows = no WebView churn crash
                w = webview.create_window("Vex Protocol", ui + "#" + __import__("urllib.parse").parse.quote(payload), x=m["x"], y=m["y"], width=m["w"], height=m["h"],
                                          frameless=True, on_top=True, focus=False, background_color="#000000", resizable=False)
                overlays.append(w)
        except Exception:
            log.exception("protocol overlay")
        time.sleep(1.2)  # let the overlay windows load so both monitors start together
        try:
            app.window.evaluate_js(f"window.vexProtocol && vexProtocol({payload}, 'main')")
        except Exception:
            log.exception("protocol main")
        for w in overlays:
            try: w.evaluate_js(f"window.vexProtocol && vexProtocol({payload}, 'side')")
            except Exception: log.exception("protocol side")
        log.info("protocol: %s started on %d monitor(s)", name, 1 + len(overlays))
        time.sleep(DUR)
        for w in overlays:
            try: w.destroy()
            except Exception: pass
        if done:
            try: done()
            except Exception: log.exception("mode done")
        else:
            say(f"{color.title()} protocol complete.")
        log.info("protocol: %s complete", name)
    finally:
        _busy.release()
