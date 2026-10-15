"""Glue: wake -> listen -> think -> act -> speak, and status for the UI."""
import re, os, json, time, random, datetime, logging, threading, subprocess, urllib.request
from . import config, tools, actlog
from .brain import Brain
from .listener import Listener, strip_wake
from .stt import STT
from .tts import TTS

log = logging.getLogger("vex.core")
HALLUCINATION = re.compile(r"[\s.,!?]*(?:thank you|thanks for watching|thank you for watching|you|so|uh|um|hmm|\.+|music|\[.*\]|\(.*\))[\s.,!?]*")
BUILTIN_GAMES = ["fortniteclient-win64-shipping.exe", "robloxplayerbeta.exe", "minecraft.windows.exe", "rocketleague.exe", "valorant-win64-shipping.exe",
                 "cs2.exe", "gta5.exe", "r5apex.exe", "overwatch.exe", "fallguys_client_game.exe", "gorilla tag.exe", "vrserver.exe"]  # 4.2: GPU-heavy games
COMMON_LINES = ["Stopped.", "Done.", "On it.", "Here you go.", "Opening everything up.", "Back to just me.", "Camera off.", "Cleared.",
                "On the panel now.", "Understood. I've left it alone.", "Say that again?", "Shall I proceed?", "Very good.", "Timer set for 5 minutes.",
                "Timer set for 10 minutes.", "No timers running.", "Here's what I can do. Apps, timers, reminders, memory, the show-me panel, PC control and questions. Just ask."]
GREETINGS = ["At your service.", "Online and ready, sir.", "Good to see you. What shall we do?", "Systems nominal. How can I help?", "I'm listening."]


def ollama_up():
    try:
        with urllib.request.urlopen(config.get("ollama_url").rstrip("/") + "/api/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_ollama():
    """Starts Vex's private Ollama if nothing is answering yet. Returns the process if we started it."""
    if ollama_up():
        return None
    exe = os.path.join(config.APP_DIR, "ollama", "ollama.exe")
    if not os.path.exists(exe):
        return None
    os.makedirs(config.LOG_DIR, exist_ok=True)
    env = dict(os.environ, OLLAMA_MODELS=os.path.join(config.APP_DIR, "ollama", "models"), OLLAMA_HOST="127.0.0.1:11434")
    proc = subprocess.Popen([exe, "serve"], env=env, creationflags=0x08000000 if os.name == "nt" else 0,
                            stdout=subprocess.DEVNULL, stderr=open(os.path.join(config.LOG_DIR, "ollama.log"), "ab"))
    for _ in range(40):
        if ollama_up():
            break
        time.sleep(0.5)
    return proc


class Vex:
    def __init__(self, emit):
        self.emit = emit  # emit(event: str, data)
        self.brain = Brain()
        self.brain.say_cb = lambda t: self.say(t)
        self.brain.emit_cb = lambda ev, d: self.emit(ev, d)
        from .chat import Engine
        self.engine = Engine(self.brain)
        self.brain.engine = self.engine
        self.engine.status_cb = lambda cid, tool: self.emit("chat_tool", {"chat": cid, "tool": tool})
        self.tray_notify = None
        self.stt = STT()
        self.tts = TTS(level_cb=lambda v: self.emit("level", {"v": v, "src": "speak"}))
        self.listener = self._new_listener()
        self.game_mode = None
        self.model_warm = False
        self._policy_lock = threading.Lock()
        self.state = "starting"
        self.status = {"stt": "loading", "llm": "starting", "tts": config.get("tts_engine"), "mic": "starting"}
        self.ollama_proc = None
        self._busy = threading.Lock()
        from .phone import PhoneBridge
        self.phone = PhoneBridge(self)

    def _new_listener(self):
        l = Listener(self._on_wake, None, lambda v: self.emit("level", {"v": v, "src": "mic"}), self._on_listener_state)
        l.on_kill = lambda: self.cancel_all("kill phrase")
        l.on_barge = self.barge_in
        return l

    # ------------------------------------------------------------ startup
    def start(self):
        threading.Thread(target=self._boot, daemon=True).start()
        from . import assist
        assist.notify_cb = self.notify
        from . import ops
        ops.core = self
        from . import pcindex
        pcindex.start_background()
        threading.Thread(target=ops.monitor_loop, daemon=True).start()
        threading.Thread(target=assist.reminder_loop, daemon=True).start()

    def notify(self, title, text):
        """Reminders / briefing: Windows notification + in-app banner + spoken."""
        self.emit("notify", {"title": title, "text": text})
        if self.tray_notify:
            try: self.tray_notify(title, text)
            except Exception: log.exception("tray notify")
        threading.Thread(target=lambda: self.say(f"{title}: {text}"), daemon=True).start()

    # ------------------------------------------------------------ supervisor: keeps everything alive
    def _supervise(self):
        while True:
            time.sleep(10)
            try:
                if not self.listener.is_alive():
                    log.warning("listener thread died, starting a new one")
                    old = self.listener
                    self.listener = self._new_listener()
                    self.listener.enabled = old.enabled
                    self.listener.start()
                    self.set_state("sleeping" if self.listener.enabled else "paused")
                if config.get("llm_backend") == "ollama" and config.get("start_ollama_automatically"):
                    if not ollama_up():
                        log.warning("ollama not answering, restarting it")
                        self.model_warm = False
                        self.status["llm"] = "restarting"; self.emit("status", self.status)
                        self.ollama_proc = ensure_ollama() or self.ollama_proc
                        if ollama_up():
                            self.status["llm"] = (config.get("ollama_fast_model") or config.get("ollama_model")) + " ready"; self.emit("status", self.status)
                    self._model_policy()
            except Exception:
                log.exception("supervisor")

    def _free_vram_mb(self):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], capture_output=True,
                                 text=True, timeout=5, creationflags=0x08000000 if os.name == "nt" else 0).stdout
            return int(out.strip().splitlines()[0])
        except Exception:
            return None

    def _model_policy(self):
        """GPU-warm when idle, GPU-free while Gorilla Tag / SteamVR run."""
        if not self._policy_lock.acquire(blocking=False):
            return
        try:
            self._model_policy_inner()
        finally:
            self._policy_lock.release()

    def _model_policy_inner(self):
        from . import winutil
        if not ollama_up():
            return
        procs = winutil.running_process_names()
        game = any(p.lower() in procs for p in list(config.get("game_mode_processes") or []) + BUILTIN_GAMES)
        try:
            from . import modes
            game = game or modes.gpu_free()  # RED / Combat mode: keep the GPU free for the game
        except Exception: pass
        if game != self.game_mode:
            self.game_mode = game
            if game:
                log.info("game/VR running: unloading model from GPU, using CPU for chat")
                self.brain.unload()
                self.brain.cpu_only, self.brain.keep_alive, self.model_warm = True, "30m", False
                self.status["llm"] = (config.get("ollama_fast_model") or config.get("ollama_model")) + " (CPU, game mode)"
                threading.Thread(target=self.brain.warmup, daemon=True).start()   # fast model preloaded in RAM so the first answer is quick
            else:
                log.info("no game/VR: GPU mode")
                if self.brain.cpu_only:
                    self.brain.unload()
                self.brain.cpu_only, self.brain.keep_alive = False, "15m"
                self.status["llm"] = config.get("ollama_model") + " ready"
            self.emit("status", self.status)
        if not game and self.model_warm:  # make sure it's really still loaded (someone may have unloaded it)
            try:
                with urllib.request.urlopen(config.get("ollama_url").rstrip("/") + "/api/ps", timeout=3) as r:
                    ours = [m for m in json.loads(r.read()).get("models", []) if m.get("name", "").startswith(config.get("ollama_fast_model") or config.get("ollama_model"))]
                # gone, or no longer "keep forever" (expiry within a year) -> warm it again
                if not ours or int(str(ours[0].get("expires_at", "0"))[:4] or 0) < datetime.date.today().year + 1:
                    self.model_warm = False
            except Exception:
                pass
        if not game and config.get("keep_model_warm") and not self.model_warm:
            free = self._free_vram_mb()
            if free is None or free >= min(2600, int(config.get("min_free_vram_mb") or 3000)):
                self.brain.keep_alive = -1
                self.model_warm = self.brain.warmup()
                if self.model_warm:
                    log.info("model kept warm on GPU (free VRAM before: %s MB)", free)
            else:
                self.brain.keep_alive = "15m"

    def _boot(self):
        actlog.write("INFO", "vex started", None, "listening" if self.listener.enabled else "listening paused")
        self.set_state("starting")
        threading.Thread(target=self._boot_llm, daemon=True).start()
        try:
            from . import voicepack
            if not voicepack.status()["ready"]:
                raise RuntimeError("voice pack not installed")
            self.status["stt"] = self.stt.load()
        except Exception as e:
            self.status["stt"] = "voice pack needed" if "voice pack" in str(e) else "error"
            if "voice pack" in str(e):
                log.info("voice pack not installed yet: typed chat works, voice after the download in Setup")
            else:
                log.exception("stt")
        self.emit("status", self.status)
        self.listener.start()
        threading.Thread(target=lambda: self.tts.prewarm(GREETINGS + COMMON_LINES), daemon=True).start()
        threading.Thread(target=self._supervise, daemon=True).start()
        try:
            self.phone.start()
        except Exception:
            log.exception("phone bridge")
        self.set_state("sleeping" if self.listener.enabled else "paused")
        try:  # 3.4 cinematic boot line
            self.emit("bootdone", {"name": config.get("assistant_name")})
            from . import product as _p0, modes as _m0
            if _p0.intro_due() and not _p0._gaming() and _m0.current() != "red":
                time.sleep(5)  # 4.1: let the window reach fullscreen and the companion HUD open, then the presentation is the boot
                threading.Thread(target=_p0.intro, daemon=True).start(); return
            if config.get("boot_voice"):
                time.sleep(4.5)  # 4.0: spoken as the boot cinematic lands on "Welcome back, sir"
                from . import product
                self.say(product.welcome_line())
            from . import product as _p
            if _p.intro_due() and not _p._gaming():
                threading.Thread(target=_p.intro, daemon=True).start()
            elif config.get("brief_on_wake") is not False:
                def _b():
                    time.sleep(9)
                    from . import product
                    product.emit("briefing", product.briefing_cards())
                threading.Thread(target=_b, daemon=True).start()
        except Exception:
            log.exception("boot line")

    def _ollama_up(self):
        return ollama_up()

    def _boot_llm(self):
        if config.get("llm_backend") == "openai_compatible" and config.get("api_key"):
            self.status["llm"] = "api: " + (config.get("api_model") or "custom"); self.emit("status", self.status); return
        if config.get("start_ollama_automatically"):
            self.ollama_proc = ensure_ollama()
        if not ollama_up():
            self.status["llm"] = "offline (simple commands still work)"; self.emit("status", self.status)
            return
        self.status["llm"] = "loading " + config.get("ollama_model"); self.emit("status", self.status)
        self._model_policy()
        ok = self.model_warm or self.brain.warmup()
        self.status["llm"] = (config.get("ollama_model") + " ready") if ok else "model missing"
        self.emit("status", self.status)

    def shutdown(self):
        self.listener.stop()
        self.tts.stop()
        # stop Vex's own private Ollama (only the copy inside the Vex folder, never another install)
        if os.name == "nt" and config.get("start_ollama_automatically"):
            od = os.path.join(config.APP_DIR, "ollama").replace("'", "''")
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"Get-CimInstance Win32_Process | Where-Object {{ $_.ExecutablePath -like '{od}\\*' }} | "
                            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"], creationflags=0x08000000, timeout=15)
        elif self.ollama_proc:
            try: self.ollama_proc.terminate()
            except Exception: pass

    # ------------------------------------------------------------ state
    def set_state(self, s):
        self.state = s
        busy = s in ("thinking", "speaking")
        if busy and not self.listener.kill_watch.is_set():
            self.listener.kill_watch.set()
        elif not busy:
            self.listener.kill_watch.clear()
        self.status["mic"] = self.listener.status
        self.emit("state", {"state": s, "status": self.status})

    def _on_listener_state(self, s):
        if s in ("paused", "nowake", "micerror") and self.state not in ("speaking", "thinking"):
            self.set_state(s)

    def say(self, text):
        text = config.brand(text)
        if not text:
            return
        self.emit("transcript", {"who": "vex", "text": text})
        self.set_state("speaking")
        self.listener.speaking.set()
        try:
            self.tts.speak(text)
            self.status["tts"] = self.tts.engine_used
        except Exception:
            log.exception("tts")
        finally:
            self.listener.mute_until = time.time() + 0.3
            self.listener.speaking.clear()

    # ------------------------------------------------------------ conversation (runs on the listener thread)
    def _greeting(self):
        g = config.get("greeting") or random.choice(GREETINGS)
        if random.random() < 0.4:
            g = random.choice(GREETINGS)
        try:  # brief proactive status remark
            from . import assist
            st = assist.pc_stats()
            if st.get("cpu", 0) >= 85: g += f" CPU is running hot at {st['cpu']} percent."
            elif st.get("disk_pct", 0) >= 92: g += f" Drive C is nearly full, sir."
            elif random.random() < 0.35:
                w = assist._wcache.get((config.get("weather_city") or "").lower())
                if w: g += f" It's {w[1]['temp']} degrees and {w[1]['desc']} outside."
        except Exception:
            pass
        if config.get("proactive_trending"):
            stamp = os.path.join(config.APP_DIR, "cache", "last_trend_day.txt")
            today = datetime.date.today().isoformat()
            try: last = open(stamp).read().strip()
            except Exception: last = ""
            if last != today:
                line = tools.proactive_trending_line()
                if line:
                    os.makedirs(os.path.dirname(stamp), exist_ok=True)
                    open(stamp, "w").write(today)
                    self.brain.pending_yes = lambda: tools.open_store_page()
                    g = g + " " + line
        return g

    def _on_wake(self, phrase, audio):
        if phrase is None:  # push-to-talk: skip the greeting, just listen
            self.converse()
            self.set_state("sleeping" if self.listener.enabled else "paused")
            return
        command = ""
        self._lat_start(time.time(), "wake")
        if phrase and audio is not None and len(audio) > 16000 * 1.2:
            try:
                command = strip_wake(self.stt.transcribe(audio), phrase)
            except Exception:
                command = ""
        self._lat["stt"] = time.time()
        if len(command.split()) >= 2:
            self.emit("transcript", {"who": "you", "text": command})
            sleep = self.run_command(command)
        else:
            sleep = False
            self.say(self._greeting())
        if not sleep:
            self.converse()
        self.set_state("sleeping" if self.listener.enabled else "paused")

    def converse(self):
        """Keep listening without the wake phrase until it goes quiet for a few seconds."""
        if self.stt.model is None and self.status.get("stt") == "voice pack needed":
            self.say("Voice control needs the voice pack first. Open Setup to download it, or type to me in the meantime.")
            return
        while True:
            self.set_state("listening")
            wait = float(config.get("conversation_timeout_s") or 600) if config.get("conversation_mode") else float(config.get("follow_up_seconds") or 8)
            audio = self.listener.capture(wait)
            if audio is None:
                return
            self.set_state("thinking")
            self._lat_start(getattr(self.listener, "speech_end", 0) or time.time(), "follow-up")
            try:
                text = self.stt.transcribe(audio)
            except Exception:
                log.exception("stt"); text = ""
            self._lat["stt"] = time.time()
            if not text or HALLUCINATION.fullmatch(text.strip().lower()):
                continue  # silence / noise that whisper turned into filler
            self.emit("transcript", {"who": "you", "text": text})
            if self.run_command(text):
                return

    def barge_in(self):
        """Stop talking (but don't cancel anything) so he can cut in; conversation mode keeps listening."""
        if self.state == "speaking":
            self.tts.stop()
            try:
                import sounddevice as sd; sd.stop()
            except Exception:
                pass
            from . import ops
            ops.feed("voice", "Interrupted - listening")

    def cancel_all(self, source="voice"):
        """'Vex stop' / stop hotkey: cancel the running action, pending confirmations, and speech."""
        actlog.CANCEL.set()
        try:
            from . import pc as _pc
            if _pc.power_pending(): _pc.cancel_power(quiet=True)
        except Exception: pass
        self.tts.stop()
        self.brain.clear_pending()
        tools._pending.update(text=None)
        actlog.write("CANCELLED", "vex stop", {"source": source}, "everything cancelled")
        self.emit("transcript", {"who": "vex", "text": "Stopped."})

    # Vex 4.2 speed: latency log (numbers only)
    def _lat_start(self, t0, kind):
        self._lat = {"t0": t0, "kind": kind}
        def first():
            L = getattr(self, "_lat", None)
            if not L or L.get("done"):
                return
            L["done"] = True; now = time.time()
            stt = L.get("stt", now) - L["t0"]; think = L.get("think", now) - L.get("stt", now)
            log.info("latency: %s end of speech -> first word %.2f s (stt %.2f, brain %.2f, voice %.2f) [%s]", L["kind"], now - L["t0"], stt,
                     max(0, L.get("think1", L.get("think", now)) - L.get("stt", now)), max(0, now - L.get("think1", L.get("think", now))), L.get("route", "?"))
        self.tts.first_cb = first

    # Vex 4.2: streamed replies - sentences are spoken by a helper thread while the model keeps generating
    def _stream_start(self):
        import queue as _q
        self._sq, self._spoken = _q.Queue(), []
        def worker(q=self._sq):
            while True:
                s = q.get()
                if s is None:
                    return
                if actlog.CANCEL.is_set():
                    continue
                self.say(s)
                if actlog.CANCEL.is_set():
                    continue
                self.set_state("thinking") if q.qsize() == 0 and not getattr(self, "_stream_done", True) else None
        self._stream_done = False
        self._sthread = threading.Thread(target=worker, daemon=True); self._sthread.start()
        def sink(sent):
            self._spoken.append(sent)
            try: self.tts.prefetch(getattr(config, "brand", lambda x: x)(sent))   # synthesis starts right away
            except Exception: pass
            self._sq.put(sent)
        return sink

    def _stream_finish(self, say):
        """Waits for the streamed sentences to finish and returns whatever part of `say` wasn't spoken yet."""
        self._stream_done = True
        self._sq.put(None)
        self._sthread.join(timeout=120)
        sp = self._spoken
        if not sp:
            return say
        nz = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
        parts = [x for x in re.split(r"(?<=[.!?])\s+", say or "") if x.strip()]
        k = 0
        while k < len(parts) and k < len(sp) and nz(parts[k]) and nz(sp[k]).startswith(nz(parts[k])[:max(1, len(nz(parts[k])) - 2)]):
            k += 1
        if k == len(sp):
            return " ".join(parts[k:])
        return ""  # reply already spoken in streamed form

    def run_command(self, text):
        """Returns True if Vex should go back to sleep."""
        with self._busy:
            actlog.CANCEL.clear()
            self.set_state("thinking")
            sink = self._stream_start()
            L = getattr(self, "_lat", None) or {}
            def sink_t(s, _sink=sink):
                L.setdefault("think1", time.time()); _sink(s)
            self.engine.sink = sink_t
            self.engine.last_model = None
            th0 = time.time()
            try:
                res = self.brain.handle(text)
            except Exception:
                log.exception("brain")
                res = {"say": "Apologies, something went wrong on my end."}
            finally:
                self.engine.sink = None
            L["think"] = time.time()
            L["route"] = getattr(self.engine, "last_model", None) or "rule"
            log.info("latency: command handled in %.0f ms (%s)", (time.time() - th0) * 1000, L["route"])
            try:
                res["say"] = self._stream_finish(res.get("say", ""))
            except Exception:
                log.exception("stream finish")
            if res.get("kill"):
                self.cancel_all("voice")
                actlog.CANCEL.clear()
            if actlog.CANCEL.is_set():  # "Vex stop" was heard while this was running
                actlog.CANCEL.clear()
                return False
            if res.get("detail"):
                self.emit("transcript", {"who": "vex", "text": res["detail"]})
            self.say(res.get("say", ""))
            after = res.get("after")
            if after:
                time.sleep(0.4)
                try: after()
                except Exception: log.exception("after")
            return bool(res.get("sleep"))

    # ------------------------------------------------------------ UI actions
    def typed(self, text):
        self.emit("transcript", {"who": "you", "text": text})
        def go():
            self.run_command(text)
            self.set_state("sleeping" if self.listener.enabled else "paused")
        threading.Thread(target=go, daemon=True).start()

    def push_to_talk(self):
        if self.state in ("speaking",):
            self.tts.stop(); return
        self.listener.ptt.set()

    def set_listening(self, on):
        self.listener.set_enabled(on)
        config.save({"listening_enabled": bool(on)})
        self.set_state("sleeping" if on else "paused")
