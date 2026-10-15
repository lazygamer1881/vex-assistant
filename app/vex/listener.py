"""Microphone loop: waits for the wake phrase (Vosk, tiny + offline), then records the command
until you stop talking and hands it to Whisper.

The mic stream only exists while Vex is listening; "Pause listening" closes it completely."""
import os, re, json, time, queue, difflib, logging, threading
import numpy as np
from . import config

log = logging.getLogger("vex.listen")
SR = 16000
BLOCK = 1600  # 100 ms


def rms(block_i16):
    f = block_i16.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(f * f)) + 1e-9)


SOUNDALIKE = {"hey": {"hey", "a", "hay", "hi", "he", "hail"}, "yo": {"yo", "your", "you", "yeah", "yoh", "joe"},
             "ok": {"ok", "okay"}, "okay": {"ok", "okay"}}
FILLERS = {"yo", "hey", "ok", "okay", "so", "um", "uh", "alright", "aight", "bro", "a", "and"}


def _word_ok(heard, want, name):
    if heard == want or heard in SOUNDALIKE.get(want, ()):
        return True
    if want == name:  # the assistant's name gets fuzzy matching ("vecks", "vax")
        return difflib.SequenceMatcher(None, heard, want).ratio() >= 0.5 and heard[:1] in (want[:1], "f", "b")
    return False


def wake_match(text, phrases, name=None):
    """True if the utterance starts with (or is) a wake phrase. Normal words must match exactly
    ('I woke up' won't wake it); only the assistant's name is fuzzy."""
    name = (name or config.get("assistant_name") or "").lower()
    words = re.sub(r"[^a-z' ]", " ", (text or "").lower()).split()
    if not words:
        return None
    for p in phrases:
        pw = p.lower().split()
        n = len(pw)
        starts = [0] + ([1] if words[0] in FILLERS else [])
        for start in starts:
            cand = words[start:start + n]
            if len(cand) == n and all(_word_ok(h, w, name) for h, w in zip(cand, pw)):
                return p
    return None


def strip_wake(text, phrase):
    """Remove the wake phrase from a Whisper transcript, keep the rest as the command."""
    t = (text or "").strip()
    low = t.lower()
    pw = phrase.lower().split()
    words = t.split()
    for start in (0, 1):
        cand = " ".join(re.sub(r"[^a-z']", "", w.lower()) for w in words[start:start + len(pw)])
        if difflib.SequenceMatcher(None, cand, " ".join(pw)).ratio() >= 0.7:
            return " ".join(words[start + len(pw):]).strip(" ,.!?")
    i = low.find(phrase.lower())
    if i >= 0:
        return t[i + len(phrase):].strip(" ,.!?")
    return t


BARGE = ["hold on", "wait wait", "one second", "hang on", "excuse me"]


class Listener(threading.Thread):
    def __init__(self, on_wake, on_command_audio, on_level, on_state):
        super().__init__(daemon=True)
        self.on_wake, self.on_command_audio, self.on_level, self.on_state = on_wake, on_command_audio, on_level, on_state
        self.q = queue.Queue(maxsize=200)
        self.stream = None
        self.mute_until = 0.0
        self.speaking = threading.Event()
        self.ptt = threading.Event()
        self.enabled = bool(config.get("listening_enabled"))
        self.running = True
        self.noise = 0.004
        # Vex 4.2: auto level + noise gate (numbers only - audio stays in memory, never saved)
        self.gain = 1.0
        self.speech_lv = 0.0
        self.calib_left = 0
        self.mic_state = "starting"   # ok / paused / error / recovering - shown as a dot on the HUD
        self.level = 0.0
        self._fails = 0
        self._starve = 0
        self.vosk_model = None
        self.status = "starting"
        # kill phrase ("Vex stop") is watched on a separate thread while Vex is busy thinking/speaking/acting
        self.kill_watch = threading.Event()
        self.kill_q = queue.Queue(maxsize=100)
        self.on_kill = lambda: None
        self.on_barge = lambda: None

    # ---------------------------------------------------------- mic
    def _cb(self, indata, frames, t, status):
        b = indata[:, 0].copy()
        try:
            self.q.put_nowait(b)
        except queue.Full:
            pass
        if self.kill_watch.is_set():
            try: self.kill_q.put_nowait(b)
            except queue.Full: pass

    def _kill_loop(self):
        from vosk import KaldiRecognizer
        while self.running:
            if self.vosk_model is None or not self.kill_watch.is_set():
                time.sleep(0.1)
                while not self.kill_q.empty():
                    try: self.kill_q.get_nowait()
                    except queue.Empty: break
                continue
            phrases = [p for p in (config.get("kill_phrases") or ["vex stop"])
                       if all(self.vosk_model.vosk_model_find_word(w) >= 0 for w in p.split())] or ["stop stop"]
            # Vex 2.5 barge-in: while Vex is talking, "hold on" / "wait wait" / "one second" cuts the speech and he keeps listening
            barge = [p for p in (BARGE if config.get("barge_in") else [])
                     if all(self.vosk_model.vosk_model_find_word(w) >= 0 for w in p.split())]
            rec = KaldiRecognizer(self.vosk_model, SR, json.dumps(phrases + barge + ["[unk]"]))
            while self.running and self.kill_watch.is_set():
                try:
                    b = self.kill_q.get(timeout=0.3)
                except queue.Empty:
                    continue
                done = rec.AcceptWaveform(b.tobytes())
                text = json.loads(rec.Result() if done else rec.PartialResult()).get("text" if done else "partial", "")
                if any(p in text for p in phrases):
                    log.info("kill phrase heard")
                    try: self.on_kill()
                    except Exception: log.exception("on_kill")
                    rec.Reset()
                elif barge and self.speaking.is_set() and any(p in text for p in barge):
                    log.info("barge-in heard")
                    try: self.on_barge()
                    except Exception: log.exception("on_barge")
                    rec.Reset()

    def _open(self):
        if self.stream is None:
            import sounddevice as sd
            self.stream = sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=BLOCK,
                                         device=config.get("mic_device"), callback=self._cb)
            self.stream.start()
            try: nm = sd.query_devices(self.stream.device)["name"]
            except Exception: nm = str(config.get("mic_device"))
            log.info("mic open: %s (setting %r)", nm, config.get("mic_device")); self._capN = 0; self._capS = 0.0
            self.calib_left = 15 if config.get("mic_autocal") is not False else 0  # ~1.5 s of room noise sets the floor
            self._calS = []; self._starve = 0; self.mic_state = "ok"

    def _reinit_audio(self):
        """Vex 4.2 auto-recovery: re-scan audio devices so an unplugged/replugged mic comes back by name."""
        if self.speaking.is_set():
            return
        try:
            import sounddevice as sd
            sd._terminate(); sd._initialize()
            log.info("audio devices re-scanned for mic recovery")
        except Exception as e:
            log.info("audio re-scan failed: %s", e)

    def _process(self, b):
        """Auto level: calibrates the noise floor on open, then scales quiet speech up (clamped)
        and gently gates steady background noise before the wake word / Whisper see it."""
        lv = rms(b); self.raw_lv = lv
        if self.calib_left > 0:
            self._calS.append(lv); self.calib_left -= 1
            if self.calib_left == 0 and self._calS:
                fl = float(np.median(self._calS))
                self.noise = min(0.03, max(0.0015, fl))
                log.info("mic calibrated: noise floor %.4f", self.noise)
        elif lv < self.threshold():
            self.noise = 0.98 * self.noise + 0.02 * lv
        if config.get("mic_agc") is not False:
            if lv > self.threshold() * 1.2:
                self.speech_lv = 0.9 * self.speech_lv + 0.1 * lv if self.speech_lv else lv
                want = 0.07 / max(self.speech_lv, 1e-4)
                self.gain = float(min(float(config.get("mic_max_gain") or 4.0), max(1.0, 0.95 * self.gain + 0.05 * want)))
            if self.gain > 1.01:
                b = np.clip(b.astype(np.float32) * self.gain, -32767, 32767).astype(np.int16)
        if config.get("noise_gate") is not False and lv < self.noise * 1.6:
            b = (b.astype(np.float32) * 0.3).astype(np.int16)   # soft gate: hum/fans fade, words don't get clipped
        return b

    def _close(self):
        if self.stream is not None:
            try:
                self.stream.stop(); self.stream.close()
            finally:
                self.stream = None
        self._flush()

    def _flush(self):
        while not self.q.empty():
            try: self.q.get_nowait()
            except queue.Empty: break

    def _get(self, timeout=0.5):
        try:
            b = self.q.get(timeout=timeout)
        except queue.Empty:
            if self.stream is not None:
                self._starve += 1
            return None
        self._starve = 0
        if self.speaking.is_set() or time.time() < self.mute_until:
            self.raw_lv = 0.0
            return np.zeros_like(b)  # don't listen to our own voice
        try:
            return self._process(b)
        except Exception:
            return b

    def set_enabled(self, on):
        self.enabled = bool(on)

    def stop(self):
        self.running = False

    def threshold(self):
        return max(float(config.get("speech_sensitivity") or 0.012), self.noise * 2.5)

    # ---------------------------------------------------------- record one command
    def capture(self, wait_s):
        """Waits up to wait_s for speech, records until ~0.8 s of silence. Returns float32 audio or None."""
        self._open()
        pre, rec = [], []
        started, silent, t0 = False, 0, time.time()
        while self.running:
            b = self._get(0.5)
            if b is None:
                if not started and time.time() - t0 > wait_s:
                    return None
                continue
            lv = getattr(self, "raw_lv", 0.0)  # decisions use the raw level (gain is for recognition only)
            self.level = min(1.0, lv * 12)
            self.on_level(self.level)
            thr = self.threshold()
            if not started:
                pre = (pre + [b])[-4:]
                if lv > thr:
                    started = True; rec = list(pre)
                elif time.time() - t0 > wait_s:
                    return None
                continue
            rec.append(b)
            if lv >= thr * 0.7:
                self.speech_end = time.time()
            silent = silent + 1 if lv < thr * 0.7 else 0
            if silent >= int(config.get("endpoint_blocks") or 6) or len(rec) > 150:
                break
        self.on_level(0.0)
        if not rec:
            return None
        a = np.concatenate(rec).astype(np.float32) / 32768.0
        return a if len(a) > SR * 0.3 else None

    # ---------------------------------------------------------- main loop
    def run(self):
        while self.running:
            try:
                self._run()
            except Exception as e:
                log.exception("listener crashed, restarting in 2 s")
                self.status = f"recovering ({type(e).__name__})"
                try: self._close()
                except Exception: self.stream = None
                time.sleep(2)

    def _run(self):
        if not getattr(self, "_kill_thread", None):
            self._kill_thread = threading.Thread(target=self._kill_loop, daemon=True)
            self._kill_thread.start()
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
            self.vosk_model = Model(os.path.join(config.MODELS_DIR, "vosk-model-small-en-us-0.15"))
            rec = KaldiRecognizer(self.vosk_model, SR)
        except Exception as e:
            log.exception("vosk failed")
            self.status = f"wake word off ({e})"
            rec = None
        utt = []
        last_level = 0
        while self.running:
            if self.ptt.is_set():
                self.ptt.clear()
                self.on_wake(None, None)  # push-to-talk = straight to listening for a command
                if rec: rec.Reset()
                utt = []
                continue
            if not self.enabled or rec is None:
                self._close()
                self.status = "paused" if rec else self.status
                self.mic_state = "paused"
                self.on_state("paused" if rec else "nowake")
                while self.running and not self.enabled and not self.ptt.is_set():
                    time.sleep(0.2)
                if rec is None and not self.ptt.is_set():
                    time.sleep(0.2)
                continue
            try:
                if self.stream is not None and (not self.stream.active or self._starve >= 8):  # mic unplugged / stalled
                    log.warning("mic %s, reconnecting", "stalled (no audio for 4 s)" if self.stream.active else "stream stopped")
                    self.mic_state = "recovering"
                    try: self._close()
                    except Exception: self.stream = None
                    self._starve = 0
                    self._reinit_audio()
                self._open()
                if self._fails:
                    log.info("mic recovered after %d attempt(s)", self._fails)
                    self._fails = 0
            except Exception as e:
                self._fails += 1
                self.mic_state = "error"
                if time.time() - getattr(self, "_errT", 0) > 60:
                    self._errT = time.time(); log.warning("mic error (device %r): %s", config.get("mic_device"), e)
                self.status = f"mic error: {e}"
                self.on_state("micerror")
                self.stream = None
                if self._fails % 2 == 0:
                    self._reinit_audio()   # replugged USB mics only show up after a device re-scan
                time.sleep(3)
                continue
            self.mic_state = "ok"
            self.status = "listening for wake phrase"
            b = self._get(0.5)
            if b is None:
                continue
            lv = getattr(self, "raw_lv", 0.0)
            self._capN = getattr(self, "_capN", 0) + 1; self._capS = getattr(self, "_capS", 0.0) + lv
            if self._capN == 50:  # level number only; audio stays in memory and is never saved
                log.info("mic capturing: avg level %.4f over 5 s (auto gain x%.1f), wake word listening%s", self._capS / 50, self.gain, "" if rec else " (wake model missing)")
            now = time.time()
            if now - last_level > 0.05:
                self.level = min(1.0, lv * 8) * 0.5
                self.on_level(self.level); last_level = now
            utt.append(b)
            if len(utt) > 80:  # keep max 8 s
                utt = utt[-80:]
            if rec.AcceptWaveform(b.tobytes()):
                text = json.loads(rec.Result()).get("text", "")
                audio = np.concatenate(utt).astype(np.float32) / 32768.0
                utt = []
                if text and text.strip() in [k.lower() for k in (config.get("kill_phrases") or [])]:
                    self.on_kill()
                    continue
                p = wake_match(text, config.get("wake_phrases") or [])
                if p:
                    log.info("wake phrase heard")
                    self.on_wake(p, audio)
                    rec.Reset()
                    self._flush()
                    utt = []
        self._close()
