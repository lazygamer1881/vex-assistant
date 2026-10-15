"""Vex desktop app: window (pywebview / Edge WebView2), tray icon, hotkey."""
import os, sys, json, time, logging, threading, subprocess
from logging.handlers import RotatingFileHandler

from . import config, winutil, tools, __version__

UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")
ICON = os.path.join(config.APP_DIR, "app", "vex.ico")


def setup_logging():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    h = RotatingFileHandler(os.path.join(config.LOG_DIR, "vex.log"), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[h], format="%(asctime)s %(name)s %(levelname)s %(message)s")


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_command():
    pyw = os.path.join(config.APP_DIR, "python", "pythonw.exe")
    script = os.path.join(config.APP_DIR, "app", "run_vex.pyw")
    return f'"{pyw}" "{script}" --minimized'


def _startup_lnk():
    return os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup", "Vex Assistant.lnk")


def _run_value():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, "VexAssistantPublic")[0]
    except Exception:
        return ""


def is_start_with_windows():
    return bool(_run_value()) or os.path.exists(_startup_lnk())


def _make_startup_lnk():
    """Fallback when the Run key write is blocked: a per-user Startup-folder shortcut (no admin, no AV changes)."""
    import subprocess
    pyw = os.path.join(config.APP_DIR, "python", "pythonw.exe")
    script = os.path.join(config.APP_DIR, "app", "run_vex.pyw")
    q = lambda x: x.replace("'", "''")
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(_startup_lnk())}');"
          f"$s.TargetPath='{q(pyw)}';$s.Arguments='\"{q(script)}\" --minimized';"
          f"$s.WorkingDirectory='{q(os.path.join(config.APP_DIR, 'app'))}';$s.Description='Vex assistant';$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, timeout=30,
                   creationflags=0x08000000)
    return os.path.exists(_startup_lnk())


def set_start_with_windows(on):
    """Per-user auto-start: HKCU Run value "Vex"; if that write is blocked, a Startup-folder shortcut instead."""
    import winreg
    if on:
        if _run_value().strip().lower() == startup_command().lower():
            return True  # already registered correctly, nothing to write
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "VexAssistantPublic", 0, winreg.REG_SZ, startup_command())
        except PermissionError:
            logging.info("start with windows: Run key blocked, using Startup-folder shortcut")
            if not _make_startup_lnk():
                raise
    else:
        try: os.remove(_startup_lnk())
        except FileNotFoundError: pass
        if _run_value():
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, "VexAssistantPublic")
    return is_start_with_windows()


class Api:
    """Functions the web UI can call (window.pywebview.api.*)."""
    def __init__(self, app):
        self._app = app

    def toggle_fullscreen(self):
        w = self._app.window
        w.toggle_fullscreen()
        self._app.fullscreen = not getattr(self._app, "fullscreen", False)
        config.save({"fullscreen": self._app.fullscreen})
        return self._app.fullscreen

    def ui_log(self, msg):
        """Dashboard diagnostics (JS errors, WebGL status) into vex.log."""
        logging.info("UI: %s", str(msg)[:500])
        return True

    def get_fullscreen(self):
        return bool(getattr(self._app, "fullscreen", False))

    def get_settings(self):
        s = config.public()
        s["start_with_windows"] = is_start_with_windows()
        s["version"] = __version__
        return s

    def save_settings(self, data):
        data = dict(data or {})
        for k in ("api_key", "streamlabs_api_token", "obs_websocket_password", "groq_key", "gemini_key", "openai_key", "anthropic_key", "ha_token", "hue_username"):
            if not data.get(k):
                data.pop(k, None)  # blank = keep the saved secret
        if "wake_phrases" in data and isinstance(data["wake_phrases"], str):
            data["wake_phrases"] = [p.strip().lower() for p in data["wake_phrases"].split(",") if p.strip()]
        for k in ("follow_up_seconds", "volume_step"):
            if k in data:
                try: data[k] = int(data[k])
                except Exception: data.pop(k)
        if "speech_sensitivity" in data:
            try: data["speech_sensitivity"] = float(data["speech_sensitivity"])
            except Exception: data.pop("speech_sensitivity")
        sw = data.pop("start_with_windows", None)
        data.pop("phone_key", None)  # only changed with the "New key" button
        if "phone_port" in data:
            try:
                data["phone_port"] = int(data["phone_port"])
                if not 1024 <= data["phone_port"] <= 65535: raise ValueError
            except Exception:
                data.pop("phone_port")
        prev_preset = config.get("voice_preset")
        config.save(data)
        if data.get("voice_preset") and data["voice_preset"] != prev_preset:
            from . import tts as _tts
            _tts.apply_preset(data["voice_preset"])
        try: self._app.vex.phone.refresh()
        except Exception: pass
        if sw is not None:
            try:
                set_start_with_windows(bool(sw))
            except PermissionError:
                logging.warning("start with windows: access denied (antivirus?)")
                return {"ok": True, "warn": "Saved, but Windows (or Norton) blocked the start-with-Windows entry."}
        warn = self.check_wake_words()
        return {"ok": True, "warn": warn}

    def check_wake_words(self):
        m = self._app.vex.listener.vosk_model
        if not m:
            return ""
        bad = [w for p in config.get("wake_phrases") for w in p.split() if m.vosk_model_find_word(w) < 0]
        return ("These words aren't in my wake-word dictionary, pick common words instead: " + ", ".join(bad)) if bad else ""

    def get_status(self):
        if not getattr(self, "_seen", False):
            self._seen = True
            logging.info("UI connected (JS bridge working)")
        v = self._app.vex
        return {"state": v.state, "status": v.status, "hotkey": config.get("push_to_talk_hotkey"), "name": config.get("assistant_name"), "sounds": bool(config.get("ui_sounds")),
                "wake": config.get("wake_phrases"), "listening": v.listener.enabled}

    def send_text(self, text):
        if text and text.strip():
            self._app.vex.typed(text.strip())

    def push_to_talk(self):
        self._app.vex.push_to_talk()

    # ---------------- Vex 2.0 chat + dashboard
    def chat_send(self, chat_id, text):
        from . import chat
        text = (text or "").strip()
        if not text:
            return {"reply": ""}
        try:
            return chat.chat_turn(self._app.vex, chat_id, text[:20000])
        except Exception as e:
            logging.exception("chat")
            return {"reply": f"Apologies, something went wrong: {e}", "chat_id": chat_id}

    def chat_confirm(self, pid, yes):
        from . import chat
        return chat.chat_confirm(self._app.vex, pid, bool(yes))

    def chat_list(self):
        from . import chat
        return chat.list_chats()

    def chat_load(self, cid):
        from . import chat
        return chat.load_chat(cid)

    def chat_delete(self, cid):
        from . import chat
        return chat.delete_chat(cid)

    def chat_new(self):
        from . import chat
        return chat.new_id()

    def dashboard(self):
        from . import assist, chat
        d = {"greeting": assist.greeting(), "brain": chat.brain_label(), "stats": assist.pc_stats(),
             "todos": assist.todos(), "reminders": [r for r in assist.reminders() if not r["done"]], "recent": chat.list_chats()[:6]}
        try: d["weather"] = assist.weather_data()
        except Exception as e: d["weather"] = {"error": str(e)}
        try:
            from . import smarthome
            d["home"] = smarthome.configured()
        except Exception:
            d["home"] = {}
        d["version"] = __version__
        try: d["lowfx"] = bool(self._app.vex.brain.cpu_only) or __import__("vex.modes", fromlist=["x"]).current() == "red"  # Gorilla Tag / SteamVR running: keep the GPU free
        except Exception: d["lowfx"] = False
        d["ui_motion"] = config.get("ui_motion") or "full"  # full | auto (follow Windows animation setting) | reduced
        from . import ops
        d["feed"] = list(ops.FEED)[:12]
        d["memories"] = [m["text"] for m in assist.memories()[-10:]]
        try:
            from . import pcindex, study
            d["index"] = pcindex.stats(); d["notes"] = study.notes()[:10]
        except Exception:
            d["index"] = {}; d["notes"] = []
        from . import extras
        try: d["channel"] = ""
        except Exception: d["channel"] = ""
        try:
            np_ = extras.now_playing_info()
            d["playing"] = (np_.get("title", "") + (" – " + np_["artist"] if np_.get("artist") else "")) if np_.get("title") else ""
        except Exception: d["playing"] = ""
        return d

    # ---------------------------------------------------------- hand control (webcam gestures, in-browser MediaPipe)
    def hand_state(self):
        try: low = bool(self._app.vex.brain.cpu_only)
        except Exception: low = False
        return {"enabled": bool(config.get("hand_control")), "camera": config.get("hand_camera") or "",
                "mouse": bool(config.get("hand_mouse")), "paused": low,
                "view": config.VIEW["mode"] if config.VIEW["seq"] else (config.get("start_view") or "ai"),
                "page": config.VIEW.get("page") or "", "look": __import__("vex.look", fromlist=["x"]).current(),
                "look_seq": __import__("vex.look", fromlist=["x"]).SEQ["n"], "name": config.get("assistant_name"), "view_seq": config.VIEW["seq"],
                "sounds": bool(config.get("ui_sounds")), "mode": __import__("vex.modes", fromlist=["x"]).current(), "mode_seq": __import__("vex.modes", fromlist=["x"]).SEQ["n"]}

    def jhud(self):
        """3.7 reactor HUD data: live PC stats plus cached weather (read-only)."""
        from . import assist
        d = {}
        try: d["st"] = assist.pc_stats()
        except Exception: d["st"] = {}
        now = time.time()
        if now - getattr(self, "_jw_t", 0) > 600:
            self._jw_t = now
            try: self._jw = assist.weather_data()
            except Exception: self._jw = {}
        d["wx"] = getattr(self, "_jw", {}) or {}
        try:
            from . import modes; d["mode"] = modes.current()
        except Exception: d["mode"] = "blue"
        try:
            d["chan"] = ""  # 4.0: channel stats removed from displays (voice "how many subs do I have" still works)
        except Exception: d["chan"] = ""
        try:
            d["todos"] = [t.get("text", "") for t in assist.todos() if not t.get("done")][:4]
            d["rem"] = [r.get("text", "") + " · " + str(r.get("due", ""))[11:16] for r in assist.reminders() if not r.get("done")][:3]
        except Exception: d["todos"], d["rem"] = [], []
        try:
            st = self._app.vex.status; d["llm"] = st.get("llm", ""); d["stt"] = st.get("stt", ""); d["mic"] = st.get("mic", "")
        except Exception: pass
        try:
            from . import modes as _m; d["panel"] = _m.panel()
        except Exception: d["panel"] = {}
        try:
            import ctypes; d["up"] = ctypes.windll.kernel32.GetTickCount64() // 1000
        except Exception: d["up"] = 0
        return d

    # ---------------- 4.0 product API
    def v40_boot(self):
        from . import product; return product.boot_info()
    def v40_welcome(self):
        from . import product
        b = product.boot_info(); line = product.welcome_line(b)
        if False:
            try: self._app.vex.say(line)
            except Exception: logging.exception("welcome")
        return line
    def v40_brief(self, spoken=False):
        from . import product
        if spoken:
            threading.Thread(target=lambda: self._app.vex.say(product.brief(True)), daemon=True).start(); return {}
        return product.briefing_cards()
    def v40_steps(self):
        from . import product; return list(product.STEPS)[:30]
    def v40_show(self, q):
        from . import product; return product.media_for(q)
    def v40_themes(self):
        from . import product, modes
        return {"cur": modes.current(), "themes": [{"k": k, "name": n, "desc": d, "color": modes.MODES[k]["color"], "mode": modes.MODES[k]["name"]} for k, n, d in product.THEMES]}
    def v40_apply_theme(self, k):
        from . import modes
        k = modes.key(k)
        if not k: return False
        modes.set_mode(k); self._app.emit("modeset", {"mode": k}); return True
    def v40_smart(self):
        from . import product; return product.smart_tiles()
    def v40_smart_save(self, d):
        sh = dict(config.get("smart_home") or {})
        for k in ("enabled", "mode_lights"):
            if k in (d or {}): sh[k] = bool(d[k])
        config.save({"smart_home": sh})
        from . import product; return product.smart_tiles()
    def v40_about(self):
        from . import product; return product.about()
    def v40_wizard(self):
        from . import product; return product.wizard_state()
    def pub_devices(self):
        from . import product; return product.audio_devices()
    def pub_ollama(self):
        from . import product; return product.ollama_status()
    def pub_ollama_pull(self, model):
        from . import product; return product.ollama_pull(model)
    def pub_open_ollama_site(self):
        import webbrowser; webbrowser.open("https://ollama.com/download/windows"); return True
    def pub_listen(self, question):
        from . import product; return product.wizard_listen(self._app.vex, question)
    def pub_mic_level(self):
        try: return {"lvl": round(float(getattr(self._app.vex.listener, "level", 0.0)), 3)}
        except Exception: return {"lvl": 0}
    def v40_wizard_save(self, d):
        from . import product; return product.wizard_save(d)
    def v40_mic_test(self):
        try: return {"level": getattr(self._app.vex, "last_level", 0), "listening": bool(self._app.vex.listener.enabled)}
        except Exception: return {"level": 0, "listening": False}
    def v40_showcase(self, on=True):
        from . import product; return product.showcase(bool(on))
    def v40_mini(self, on=True):
        from . import product; return product.mini_orb(bool(on))
    def v40_intro(self):
        from . import product; threading.Thread(target=product.intro, args=(True,), daemon=True).start(); return True
    def v40_skip(self):
        from . import product; return product.skip_intro()
    def v40_ptt(self):
        try: self._app.vex.push_to_talk(); return True
        except Exception: return False
    def v42_status(self):
        """Vex 4.2 HUD: mic state + a single level number (no audio, no waveform) and running timers."""
        d = {"mic": "off", "lvl": 0.0, "timers": []}
        try:
            l = self._app.vex.listener
            d["mic"] = "paused" if not l.enabled else getattr(l, "mic_state", "ok")
            d["lvl"] = round(float(getattr(l, "level", 0.0)), 3) if l.enabled else 0.0
            d["state"] = getattr(self._app.vex, "state", "")
        except Exception:
            pass
        try:
            from . import assist
            d["timers"] = [t for t in assist.active_timers() if t["kind"] == "timer" or t["left"] < 3600][:3]
        except Exception:
            pass
        return d

    def v42_tab(self, tab):
        """4.2 dashboard tabs: live data for the System / Activity tabs."""
        from . import tabs42
        if tab == "system": return tabs42.system_data()
        if tab == "activity": return tabs42.activity_data()
        return {}

    def v42_help(self, on=False):
        from . import product; product.emit("help42", {"on": bool(on)}); return True

    # ---- 4.3: permissions, crash report, updates, voice pack, Ollama auto-setup
    def v43_perms(self):
        from . import v43; return v43.perms()
    def v43_perm_set(self, k, on):
        from . import v43; return v43.perm_set(k, on)
    def v43_update_check(self):
        from . import updatecheck; return updatecheck.check()
    def v43_open_url(self, url):
        import webbrowser
        if isinstance(url, str) and url.lower().startswith("https://"):
            webbrowser.open(url); return True
        return False
    def v43_crash_info(self):
        from . import crashreport; return crashreport.info()
    def v43_crash_open(self):
        from . import v43; return v43.crash_open()
    def v43_crash_copy(self):
        from . import v43; return v43.crash_copy()
    def v43_voicepack(self):
        from . import voicepack; return voicepack.status()
    def v43_voicepack_install(self):
        from . import voicepack; return voicepack.install()
    def v43_voicepack_cancel(self):
        from . import voicepack; return voicepack.cancel()
    def v43_restart(self):
        from . import v43; return v43.restart(self._app)
    def v43_speaker_test(self):
        from . import v43; return v43.speaker_test(self._app.vex)
    def v43_ollama_install(self):
        from . import v43; return v43.ollama_install()
    def v43_ollama_job(self):
        from . import v43; return v43.ollama_job()

    def v40_idle(self):
        from . import product; return {"idle": product.idle_seconds(), "after": int(config.get("wallpaper_idle_min") or 10) * 60, "on": config.get("idle_wallpaper") is not False}

    def bphud(self):
        """3.9 companion blueprint HUD data (read-only): jhud + channel growth, activity feed, mode colour, temp message."""
        d = self.jhud()
        from . import modes, ops, displays
        d["growth"] = {}
        try: d["feed"] = list(ops.FEED)[:10]
        except Exception: d["feed"] = []
        m = modes.MODES.get(d.get("mode") or "blue", {}); d["mcol"] = m.get("color", ""); d["mname"] = m.get("name", "")
        d["msg"] = displays.TEMP.get("msg") if displays.TEMP.get("until", 0) > time.time() else None
        d["priv"] = (d.get("mode") == "black")
        return d

    def mode_panel(self):
        from . import modes
        return modes.panel()

    def mode_open(self, name):
        """Mode panel quick-open buttons. Whitelisted; opening OBS never starts a recording or stream."""
        if name not in ("obs", "capcut", "youtube studio", "gorilla tag", "steam", "spotify"):
            return "Not allowed."
        from . import tools
        return tools.open_apps([name])

    def mode_scan(self):
        try: return self._app.vex.brain._do_scan()
        except Exception as e: return str(e)

    def page_done(self):
        config.VIEW["page"] = ""; return True

    # ---------------------------------------------------------- 3.2: connections, accounts, look, displays
    def conn_list(self):
        from . import connections; return connections.listing()
    def conn_save(self, name, fields):
        from . import connections; return connections.save(name, fields)
    def conn_test(self, name):
        from . import connections; return connections.test(name)
    def conn_route(self, brain, hard):
        from . import connections; return connections.set_route(brain, hard)
    def acct_list(self):
        from . import accounts; return accounts.listing()
    def acct_connect(self, name, client_id, client_secret=""):
        from . import accounts; return accounts.connect(name, client_id, client_secret)
    def acct_disconnect(self, name):
        from . import accounts; return accounts.disconnect(name)
    def acct_discord(self, url):
        from . import accounts; return accounts.set_discord(url)
    def look_get(self):
        from . import look; return {"look": look.current(), "presets": [p.title() for p in look.PRESETS]}
    def look_preset(self, name):
        from . import look; return look.handle(name.lower() + " theme")
    def look_undo(self):
        from . import look; return look.undo()
    def look_reset(self):
        from . import look; return look.handle("reset look")
    def disp_info(self):
        from . import displays; return displays.info()
    def disp_mode(self, mode):
        from . import displays; return displays.set_mode(mode)
    def disp_move(self, n):
        from . import displays; return displays.move_to(int(n))
    def disp_clickthrough(self, on):
        from . import displays; return displays.set_clickthrough(on)
    def hud_data(self):
        from . import assist, ops
        d = {"stats": assist.pc_stats(), "feed": list(ops.FEED)[:8], "name": config.get("assistant_name"), "state": self._app.vex.state,
             "status": self._app.vex.status if isinstance(self._app.vex.status, str) else "", "version": __version__}
        try: d["reminders"] = [r for r in assist.reminders() if not r["done"]][:4]
        except Exception: d["reminders"] = []
        from . import look; d["look"] = look.current(); d["style"] = config.get("hud_style") or "compact"
        try: d["todos"] = [t for t in assist.todos() if not t.get("done")][:8]
        except Exception: d["todos"] = []
        try:
            from . import displays; d["monitors"] = displays.monitors()
        except Exception: d["monitors"] = []
        try:
            with open(os.path.join(config.LOG_DIR, "vex.log"), "rb") as f:
                f.seek(0, 2); f.seek(max(0, f.tell() - 9000))
                lines = f.read().decode("utf8", "replace").splitlines()[1:]
            import re as _re
            d["log"] = [_re.sub(r"^\d{4}-\d\d-\d\d (\d\d:\d\d:\d\d),\d+ ", r"\1 ", l)[:140] for l in lines if " INFO " in l or " WARNING " in l][-34:]
        except Exception: d["log"] = []
        try:
            from . import displays as _dp; d["msg"] = _dp.TEMP.get("msg")
        except Exception: d["msg"] = None
        try: d["uptime"] = int(time.time() - self._app.started_at)
        except Exception: d["uptime"] = 0
        return d

    def disp_style(self, style):
        from . import displays; return displays.set_style(style)

    def set_view(self, mode):
        config.VIEW["mode"] = "full" if mode == "full" else "ai"
        return config.VIEW["mode"]

    def hand_set(self, on):
        config.save({"hand_control": bool(on)})
        return self.hand_state()

    def hand_wake(self):
        """Fist held 1s: wake Vex (or stop it talking / go back to sleep)."""
        v = self._app.vex
        if v.state in ("sleeping", "paused"):
            v.push_to_talk(); return "wake"
        v.cancel_all("gesture"); return "sleep"

    def hand_mouse(self, fx, fy, ev="move", amount=0):
        """Real Windows mouse - only when 'Control real mouse' is on in Settings."""
        if not config.get("hand_mouse"):
            return False
        try:
            l, t, w, h = winutil.virtual_screen()
            x, y = l + int(max(0.0, min(1.0, float(fx))) * (w - 1)), t + int(max(0.0, min(1.0, float(fy))) * (h - 1))
            if ev in ("move", "down", "up"):
                winutil.user32.SetCursorPos(x, y)
            if ev == "down": winutil.mouse_button(True)
            elif ev == "up": winutil.mouse_button(False)
            elif ev == "click": winutil.click(x, y)
            elif ev == "wheel": winutil.mouse_wheel(int(amount))
            return True
        except Exception:
            logging.exception("hand_mouse"); return False

    def hud_stats(self):
        from . import assist
        return assist.pc_stats()

    def todo_add(self, text):
        from . import assist
        assist.add_todo(text); return assist.todos()

    def todo_toggle(self, tid):
        from . import assist
        t = assist.todos()
        for x in t:
            if x["id"] == tid: x["done"] = not x["done"]
        assist.save("todos.json", t); return t

    def todo_remove(self, tid):
        from . import assist
        t = [x for x in assist.todos() if x["id"] != tid]; assist.save("todos.json", t); return t

    def reminder_add(self, text, when):
        from . import assist
        return {"msg": assist.set_reminder(text, when), "list": [r for r in assist.reminders() if not r["done"]]}

    def reminder_cancel(self, rid):
        from . import assist
        assist.cancel_reminder(rid); return [r for r in assist.reminders() if not r["done"]]

    def memory_list(self):
        from . import assist
        return assist.memories()

    def memory_add(self, text):
        from . import assist
        assist.remember(text); return assist.memories()

    def memory_edit(self, mid, text):
        from . import assist
        m = assist.memories()
        for x in m:
            if x["id"] == mid: x["text"] = (text or "").strip()[:300]
        m = [x for x in m if x["text"]]
        assist.save("memory.json", m); return m

    def memory_delete(self, mid):
        from . import assist
        m = [x for x in assist.memories() if x["id"] != mid]; assist.save("memory.json", m); return m

    def stop_all(self):
        self._app.vex.cancel_all("button"); self._app.vex.engine.pending = None

    def set_listening(self, on):
        self._app.vex.set_listening(bool(on))

    def hue_pair(self, ip=""):
        from . import smarthome
        return smarthome.hue_pair(ip)

    def ha_test(self):
        from . import smarthome
        return smarthome.ha_test()

    def test_voice(self):
        threading.Thread(target=lambda: self._app.vex.say(("Good evening. " + config.get("assistant_name") + " at your service. Shall I carry on?") if config.get("voice_style") == "butler" else ("Yo, it's " + config.get("assistant_name") + ". Sounding good?")), daemon=True).start()

    def get_phone_info(self):
        info = self._app.vex.phone.info()
        try:
            import segno
            qr = segno.make(info["pair_url"], error="m") if info["pair_url"] else None
            info["qr_svg"] = qr.svg_inline(scale=5, dark="#0a0a10", light="#ffffff", border=3) if qr else ""
        except Exception:
            logging.exception("qr")
            info["qr_svg"] = ""
        return info

    def new_phone_key(self):
        from . import phone, actlog
        config.save({"phone_key": phone.new_key()})
        actlog.write("INFO", "phone key changed", None, "old phone key no longer works")
        return self.get_phone_info()

    def list_speakers(self):
        try:
            import sounddevice as sd
            api0 = sd.query_hostapis(0)["name"]; out = []
            for d in sd.query_devices():
                if d["max_output_channels"] > 0 and sd.query_hostapis(d["hostapi"])["name"] == api0 and d["name"] not in out and "Sound Mapper" not in d["name"]:
                    out.append(d["name"])
            return out
        except Exception:
            return []

    def list_mics(self):
        try:
            import sounddevice as sd
            out, seen = [], set()
            default_api = sd.query_hostapis(0)["name"]
            for i, d in enumerate(sd.query_devices()):
                if d["max_input_channels"] > 0 and sd.query_hostapis(d["hostapi"])["name"] == default_api and d["name"] not in seen:
                    seen.add(d["name"]); out.append({"id": i, "name": d["name"]})
            return out
        except Exception:
            return []


class App:
    def __init__(self, minimized=False):
        from .core import Vex
        self.window = None
        self.tray = None
        self.quitting = False
        self.minimized = minimized
        self._last_level = 0
        self.vex = Vex(self.emit)

    def emit(self, event, data):
        if event == "transcript" and isinstance(data, dict) and data.get("who") == "vex":
            try:
                from . import tabs42; tabs42.note(data.get("text", ""))
            except Exception: pass
        if not self.window:
            return
        if isinstance(data, dict) and event != "level":
            data = {k: (config.brand(v) if k in ("text", "title", "say", "status", "line", "greeting", "msg") and isinstance(v, str) else v) for k, v in data.items()}
        elif isinstance(data, str):
            data = config.brand(data)
        if event == "notify":
            try:
                from . import modes, ops
                if modes.muted():  # RED / BLACK: alerts go quietly to the activity feed only
                    ops.FEED.appendleft({"t": time.strftime("%I:%M %p").lstrip("0"), "kind": "muted", "text": f"{(data or {}).get('title','')}: {(data or {}).get('text','')}"}); return
            except Exception: logging.exception("mute")
        if event == "notify" or (event == "transcript" and isinstance(data, dict) and data.get("who") == "vex" and len(str(data.get("text", ""))) > 320):
            try:  # alerts and long answers also go to the other monitor for ~20s
                from . import displays
                if event == "notify": displays.show_temp(20, (data or {}).get("title", "Alert"), (data or {}).get("text", ""))
                else: displays.show_temp(25, config.brand("VEX // OUTPUT"), data.get("text", ""))
            except Exception: logging.exception("show_temp")
        if event == "level":
            now = time.time()
            if now - self._last_level < 0.045:
                return
            self._last_level = now
        try:
            self.window.evaluate_js(f"window.vexOn && window.vexOn({json.dumps(event)}, {json.dumps(data)})")
        except Exception:
            pass

    # ---------------- tray
    def make_tray(self):
        import pystray
        from PIL import Image
        img = Image.open(ICON) if os.path.exists(ICON) else Image.new("RGB", (64, 64), (139, 92, 246))
        menu = pystray.Menu(
            pystray.MenuItem(config.brand("Open Vex"), lambda: self.show(), default=True),
            pystray.MenuItem("Talk now (push to talk)", lambda: self.vex.push_to_talk()),
            pystray.MenuItem(config.brand("Stop what Vex is doing"), lambda: self.vex.cancel_all("tray")),
            pystray.MenuItem("Listening for wake phrase", lambda: self.vex.set_listening(not self.vex.listener.enabled),
                             checked=lambda item: self.vex.listener.enabled),
            pystray.MenuItem("Mini orb", lambda: __import__("vex.product", fromlist=["x"]).mini_orb(True)),
            pystray.MenuItem("Theme gallery", lambda: (self.show(), self.emit("page", {"page": "themes"}))),
            pystray.MenuItem(config.brand("About Vex"), lambda: (self.show(), self.emit("page", {"page": "about"}))),
            pystray.MenuItem(config.brand("Quit Vex"), lambda: self.quit()),
        )
        self.tray = pystray.Icon("Vex", img, config.brand(f"Vex {__version__} · Your desktop, awake."), menu)
        self.tray.run_detached()
        self.vex.tray_notify = lambda title, text: self.tray.notify(text[:250], title)

    def _show_listener(self):
        """Lets a second launch (Desktop shortcut) pop this window up instead of starting another Vex."""
        if not winutil.IS_WIN:
            return
        import ctypes
        from .watchdog import SHOW_EVENT
        k = ctypes.windll.kernel32
        k.CreateEventW.restype = ctypes.c_void_p
        k.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        h = k.CreateEventW(None, False, False, SHOW_EVENT)
        while True:
            if k.WaitForSingleObject(h, 0xFFFFFFFF) == 0:
                self.show()

    def show(self):
        if self.window:
            self.window.show(); self.window.restore()

    def quit(self):
        self.quitting = True
        try: self.vex.shutdown()
        except Exception: pass
        try: self.tray and self.tray.stop()
        except Exception: pass
        try: self.window.destroy()
        except Exception: pass
        os._exit(0)

    def on_closing(self):
        if self.quitting or not config.get("close_to_tray"):
            self.quit(); return True
        self.window.hide()
        return False

    def _allow_camera(self):
        """Let only Vex's own local dashboard (127.0.0.1) use the webcam, without a WebView2 popup."""
        for _ in range(40):
            try:
                form = self.window.native
                wv = form.browser.webview
                break
            except Exception:
                time.sleep(0.5)
        else:
            logging.warning("hand: no native webview for camera permission"); return
        def on_perm(sender, args):
            try:
                kind = str(args.PermissionKind)
                if kind == "Camera" and str(args.Uri).startswith("http://127.0.0.1:"):
                    from Microsoft.Web.WebView2.Core import CoreWebView2PermissionState
                    args.State = CoreWebView2PermissionState.Allow
                    logging.info("hand: camera permission granted to dashboard")
            except Exception:
                logging.exception("hand: permission")
        done = []
        def attach():
            try:
                if done or wv.CoreWebView2 is None: return
                wv.CoreWebView2.PermissionRequested += on_perm
                done.append(1)
                logging.info("hand: camera permission handler ready")
            except Exception:
                done.append(0); logging.exception("hand: attach permission handler")
        try:
            from System import Action
            for _ in range(60):   # BeginInvoke (async) so this thread never blocks the UI thread
                form.BeginInvoke(Action(attach))
                time.sleep(0.5)
                if done: return
            logging.warning("hand: CoreWebView2 never became ready")
        except Exception:
            logging.exception("hand: invoke")

    def run(self):
        import webview
        self.api = Api(self)
        config.write_ui_brand()
        self.window = webview.create_window(f"{config.get('assistant_name')}", UI, js_api=self.api, width=1240, height=800,
                                            min_size=(860, 560), background_color="#0a0a10", hidden=self.minimized)
        try:  # tell the dashboard when the window is minimized so animations pause (WebView2 visibility can be unreliable)
            self.window.events.minimized += lambda *a: self.window.evaluate_js("window.__vexMin=true")
            self.window.events.restored += lambda *a: self.window.evaluate_js("window.__vexMin=false")
        except Exception: pass
        self.window.events.closing += self.on_closing

        self.started_at = time.time()
        def started():
            threading.Thread(target=self._show_listener, daemon=True).start()
            if config.get("hand_control") and not config.get("hand_control_remember"):
                config.save({"hand_control": False})  # camera always starts OFF unless the user opted in to remember it
            logging.info("hand: control %s (camera %s)", "on" if config.get("hand_control") else "off", "may open" if config.get("hand_control") else "will not open")
            if config.get("start_page"):
                config.VIEW["page"] = config.get("start_page")
            try:
                from . import displays
                displays.APP["app"] = self
                logging.info("displays: %s", ", ".join(f"#{m['n']} {m['w']}x{m['h']}@{m['x']}" for m in displays.monitors()))
                threading.Thread(target=displays.watch_game_mode, daemon=True).start()
                from . import product; product.wrap_tools()
                def _seq():  # one-shot test sequence: [[seconds_after_start, command], ...]; cleared on first use
                    q = list(config.get("demo_seq") or [])
                    logging.info("demo_seq: %d items", len(q))
                    if not q: return
                    config.save({"demo_seq": []}); t0 = time.time()
                    from . import product
                    for it in q:
                        try:
                            if isinstance(it, str): at, c = it.split("|", 1); at = float(at)
                            else: it = it.get("value", it) if isinstance(it, dict) else it; at, c = float(it[0]), str(it[1])
                        except Exception: logging.exception("demo_seq item %r", it); continue
                        time.sleep(max(0, t0 + at - time.time()))
                        try:
                            logging.info("demo_seq %s: %s", at, c)
                            if c == "brief": product.emit("briefing", product.briefing_cards()); continue
                            if c == "close": product.emit("page", {"page": ""}); continue
                            r = product.command(c, c) or self.vex.brain._v32(c, c) or {}
                            if r.get("say"): self.vex.say(r["say"])
                            (r.get("after") or (lambda: None))()
                        except Exception: logging.exception("demo_seq")
                threading.Thread(target=_seq, daemon=True).start()
                def _demo():
                    c = config.get("demo_protocol")
                    if not c: return
                    config.save({"demo_protocol": ""}); time.sleep(15)
                    if c == "scan":
                        self.vex.say("Running a full diagnostic, sir. " + self.vex.brain._do_scan()); return
                    if c.endswith(" mode"):  # one-shot test of a purpose mode, same path as the voice command
                        r = self.vex.brain._v32(c, c) or {}
                        self.vex.say(r.get("say", "")); (r.get("after") or (lambda: None))(); return
                    from . import protocol
                    self.vex.say(f"Very good, sir. Initiating {c} protocol.")
                    protocol.run(c, self.vex.say)
                threading.Thread(target=_demo, daemon=True).start()
                def _disp():
                    time.sleep(10)
                    if (config.get("main_monitor") or 2) != 2: displays.place_main()
                    displays.sync_hud()
                threading.Thread(target=_disp, daemon=True).start()
            except Exception:
                logging.exception("displays")
            threading.Thread(target=self._allow_camera, daemon=True).start()
            try: self.make_tray()
            except Exception: logging.exception("tray")
            hk = winutil.Hotkey(config.get("push_to_talk_hotkey") or "ctrl+alt+v", self.vex.push_to_talk)
            hk.start()
            stop_hk = winutil.Hotkey(config.get("stop_hotkey") or "ctrl+alt+x", lambda: self.vex.cancel_all("hotkey"))
            stop_hk.start()
            self.vex.start()
            self.fullscreen = False
            if config.get("fullscreen"):
                def _fs():   # after the window has moved to its monitor, so fullscreen lands there
                    time.sleep(8)
                    try:
                        self.window.toggle_fullscreen(); self.fullscreen = True
                        self.window.evaluate_js("fsShow(true)")
                    except Exception:
                        logging.exception("fullscreen")
                threading.Thread(target=_fs, daemon=True).start()
            time.sleep(1.0)
            logging.info("hotkey %s registered: %s", config.get("push_to_talk_hotkey"), hk.ok)
        webview.start(started, gui="edgechromium", private_mode=False,
                      storage_path=os.path.join(config.APP_DIR, "cache", "webview"))


def main():
    try:
        import faulthandler; faulthandler.dump_traceback_later(40, repeat=False, file=open(os.path.join(config.LOG_DIR,'stack.txt'),'w'))
    except Exception: pass
    winutil.set_dpi_aware()
    setup_logging()
    # crash diagnostics: native crashes -> logs/crash.log, and log every exit
    try:
        import faulthandler, atexit
        os.makedirs(config.LOG_DIR, exist_ok=True)
        _fh = open(os.path.join(config.LOG_DIR, "crash.log"), "a", buffering=1)
        _fh.write(f"--- start pid {os.getpid()} {time.ctime()} {sys.argv[1:]}\n")
        faulthandler.enable(_fh)
        atexit.register(lambda: logging.info("process exiting normally (pid %s)", os.getpid()))
    except Exception:
        pass
    logging.info("Vex %s starting pid=%s args=%s", __version__, os.getpid(), sys.argv[1:])
    config.load()
    if "--selftest" not in sys.argv and "--child" not in sys.argv and "--no-watchdog" not in sys.argv:
        from . import watchdog
        watchdog.run(minimized="--minimized" in sys.argv)
        return
    if "--selftest" in sys.argv:
        os.makedirs(os.path.join(config.APP_DIR, "cache"), exist_ok=True)
        from . import selftest
        selftest.run(); return
    if not winutil.single_instance():
        from . import watchdog
        if "--minimized" not in sys.argv:
            watchdog.signal_show()
        sys.exit(3)
    os.makedirs(os.path.join(config.APP_DIR, "cache"), exist_ok=True)
    config.load()
    if "--selftest" in sys.argv:
        from . import selftest
        selftest.run(); return
    App(minimized="--minimized" in sys.argv).run()


if __name__ == "__main__":
    main()
