"""Voice out: edge-tts (free, online, natural) -> Piper (offline) -> Windows built-in voice."""
import os, io, re, sys, time, wave, asyncio, hashlib, logging, tempfile, threading, subprocess
import numpy as np
from . import config

log = logging.getLogger("vex.tts")
CACHE = os.path.join(config.APP_DIR, "cache", "tts")


def polish(audio, sr):
    """Subtle 'AI' polish: gentle high-cut, short room reverb, soft limiter. Original DSP, keeps speech clear."""
    x = audio.astype(np.float32) / 32768.0
    a = 0.35  # one-pole low-pass blend (softens harsh highs slightly)
    y = np.empty_like(x); acc = 0.0
    for i in range(0, len(x), 4096):  # vectorised-ish one-pole filter
        seg = x[i:i + 4096]; out = np.empty_like(seg)
        for j, v in enumerate(seg):
            acc += a * (v - acc); out[j] = acc
        y[i:i + 4096] = out
    y = 0.55 * x + 0.45 * y
    tail = int(sr * 0.25); r = np.concatenate([y, np.zeros(tail, np.float32)])
    wet = np.zeros_like(r)
    for ms, g in ((23, .22), (37, .16), (53, .11), (71, .07), (97, .045)):
        d = int(sr * ms / 1000); wet[d:] += r[:-d] * g
    r = r + wet * 0.6
    r = np.tanh(r * 1.1) / np.tanh(1.1)
    return (np.clip(r, -1, 1) * 32767).astype(np.int16)


def breath(sr, dur):
    """Synthesised soft in-breath (original): band-limited noise with a smooth swell, about -40 dB."""
    n = int(sr * dur); rng = np.random.default_rng(n)
    x = rng.standard_normal(n + 64).astype(np.float32)
    lo = np.convolve(x, np.ones(24) / 24, "same"); hi = np.convolve(x, np.ones(3) / 3, "same")
    y = (hi - lo)[32:32 + n]                       # crude band-pass, airy
    env = np.sin(np.linspace(0, np.pi, n)) ** 2 * np.linspace(0.6, 1.0, n)
    y = y / (np.abs(y).max() + 1e-6) * env * 0.012
    return (y * 32767).astype(np.int16)


class TTS:
    def __init__(self, level_cb=None):
        self.level_cb = level_cb or (lambda v: None)
        self.engine_used = None
        self._piper = None
        self._stop = threading.Event()
        os.makedirs(CACHE, exist_ok=True)
        import concurrent.futures as _cf
        self._pool = _cf.ThreadPoolExecutor(max_workers=3)   # 4.2 speed: sentences synthesise in parallel
        self._pre = {}

    def _workers_ok(self):
        return (config.get("tts_engine") or "edge") == "edge"   # local engines aren't thread-safe: keep them serial

    def _plan(self, text):
        from . import voice
        br, bp = self.base_prosody()
        return voice.plan(text, br, bp)

    def prefetch(self, text):
        """4.2 speed: start synthesising a sentence now (called while the model is still writing the next one)."""
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text or text in self._pre or config.get("voice_human") is False or not self._workers_ok():
            return
        try:
            plan = self._plan(text)
            self._pre[text] = (plan, [self._pool.submit(self.synth, c[0], c[1], c[2], c[4]) for c in plan])
        except Exception:
            log.exception("prefetch")

    def prewarm(self, phrases):
        """4.2 speed: pre-generate common short lines into the voice cache (synthetic assistant voice only)."""
        n = 0
        for t in phrases:
            try:
                for c in self._plan(re.sub(r"\s+", " ", t).strip()):
                    self.synth(c[0], c[1], c[2], c[4]); n += 1
            except Exception:
                pass
        log.info("voice cache: %d common phrase chunks ready", n)

    # -------- synth: return (int16 mono samples, sample_rate)
    def base_prosody(self):
        voice = config.get("edge_voice") or "en-GB-RyanNeural"
        if voice.startswith("en-GB") and config.get("voice_style") == "butler":
            return config.get("voice_rate") or "-1%", config.get("voice_pitch") or "-4Hz"   # 3.7.1: a touch quicker than the old -8%
        return config.get("edge_rate") or "+0%", config.get("edge_pitch") or "+0Hz"

    def _edge(self, text, rate=None, pitch=None, volume=None):
        import edge_tts, miniaudio
        voice = config.get("edge_voice") or "en-GB-RyanNeural"
        br, bp = self.base_prosody()
        rate, pitch = rate or br, pitch or bp
        volume = volume or "+0%"
        key = hashlib.sha1(f"{voice}|{rate}|{pitch}|{volume}|{text}".encode()).hexdigest()[:20]
        path = os.path.join(CACHE, key + ".mp3")
        if not os.path.exists(path):
            async def go():
                buf = bytearray()
                async for ch in edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume).stream():
                    if ch["type"] == "audio":
                        buf.extend(ch["data"])
                return bytes(buf)
            data = asyncio.run(asyncio.wait_for(go(), timeout=12))
            if not data:
                raise RuntimeError("edge-tts returned no audio")
            if len(text) < 80:  # cache short lines (greetings, confirmations)
                with open(path, "wb") as f:
                    f.write(data)
        else:
            data = open(path, "rb").read()
        d = miniaudio.decode(data, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=24000)
        return np.frombuffer(d.samples, dtype=np.int16), 24000

    def _kokoro(self, text):
        """Kokoro-82M ONNX on CPU. kokoro_voice can blend voices, e.g. 'bm_george:0.6,bm_lewis:0.4'."""
        if getattr(self, "_kk", None) is None:
            from kokoro_onnx import Kokoro
            d = os.path.join(config.MODELS_DIR, "kokoro")
            self._kk = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
        spec = config.get("kokoro_voice") or "bm_george"
        if ":" in spec or "," in spec:
            style = None
            for part in spec.split(","):
                n, _, w = part.partition(":")
                s = self._kk.get_voice_style(n.strip()) * float(w or 1)
                style = s if style is None else style + s
        else:
            style = spec.strip()
        a, sr = self._kk.create(text, voice=style, speed=float(config.get("kokoro_speed") or 0.86), lang="en-gb")
        return (np.clip(a, -1, 1) * 32767).astype(np.int16), sr

    def _piper_synth(self, text):
        if self._piper is None:
            from piper import PiperVoice
            pv = config.get("piper_voice_gb") if (config.get("edge_voice") or "").startswith("en-GB") else config.get("piper_voice")
            onnx = os.path.join(config.MODELS_DIR, "piper", pv + ".onnx")
            if not os.path.exists(onnx):
                onnx = os.path.join(config.MODELS_DIR, "piper", config.get("piper_voice") + ".onnx")
            self._piper = PiperVoice.load(onnx)
        chunks, sr = [], 22050
        for c in self._piper.synthesize(text):
            chunks.append(c.audio_int16_array); sr = c.sample_rate
        return np.concatenate(chunks), sr

    def _windows(self, text):
        fd, path = tempfile.mkstemp(suffix=".wav"); os.close(fd)
        safe = text.replace("'", "''")
        ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.Rate=1; $s.SetOutputToWaveFile('{path}'); $s.Speak('{safe}'); $s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=20, creationflags=0x08000000)
        with wave.open(path) as w:
            sr, data = w.getframerate(), w.readframes(w.getnframes())
        os.remove(path)
        return np.frombuffer(data, dtype=np.int16), sr

    def synth(self, text, rate=None, pitch=None, volume=None):
        order = {"edge": ["edge", "windows"], "windows": ["windows"]}.get(config.get("tts_engine"), ["edge", "windows"])
        for eng in order:
            try:
                fn = {"kokoro": self._kokoro, "edge": self._edge, "piper": self._piper_synth, "windows": self._windows}[eng]
                audio, sr = fn(text, rate, pitch, volume) if eng == "edge" else fn(text)
                self.engine_used = eng
                if config.get("voice_fx"):
                    audio = polish(audio, sr)
                return audio, sr
            except Exception as e:
                log.info("tts %s failed: %s", eng, e)
        raise RuntimeError("no TTS engine worked")

    def stop(self):
        self._stop.set()

    def speak(self, text):
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return
        if config.get("voice_human") is not False:
            return self._speak_human(text)
        parts = [x for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]
        if len(parts) < 2 or len(text) < 90:
            audio, sr = self.synth(text)
            self.play(audio, sr)
            return
        # pipeline: synthesize the next sentence while the current one plays (first words come out sooner)
        import concurrent.futures as cf
        self._stop.clear()
        with cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(self.synth, parts[0])
            for i in range(len(parts)):
                audio, sr = fut.result()
                if i + 1 < len(parts):
                    fut = ex.submit(self.synth, parts[i + 1])
                if self._stop.is_set():
                    break
                self.play(audio, sr)
                if self._stop.is_set():
                    break

    def _speak_human(self, text):
        """3.7.1: cleaned, conversational text spoken chunk by chunk with per-sentence prosody and natural pauses.
        The next chunk is synthesised while the current one plays."""
        pre = self._pre.pop(text, None)
        if pre:
            plan, futs = pre
        else:
            plan = self._plan(text)
            if not plan:
                return
            if self._workers_ok():   # all chunks start at once; they play in order as they finish
                futs = [self._pool.submit(self.synth, c[0], c[1], c[2], c[4]) for c in plan]
            else:
                futs = None
        if len(self._pre) > 20:
            self._pre.clear()
        self._stop.clear()
        if True:
            for i, (chunk, rate, pitch, pause, vol) in enumerate(plan):
                audio, sr = futs[i].result() if futs else self.synth(chunk, rate, pitch, vol)
                if self._stop.is_set():
                    break
                gap = max(0, pause - 150)   # play() already pads ~150 ms
                if gap:
                    sil = np.zeros(int(sr * gap / 1000), np.int16)
                    if gap >= 100 and config.get("voice_breaths") is not False and (hash(chunk) % 100) < 55:
                        b = breath(sr, min(0.2, gap / 1000 * 0.8)); sil[:len(b)] += b   # tiny, quiet in-breath
                    audio = np.concatenate([audio, sil])
                self.play(audio, sr)
                if self._stop.is_set():
                    break

    @staticmethod
    def out_device():
        """Index of the chosen output (matched by name, MME host API), or None for the Windows default."""
        name = (config.get("speaker_device") or "").strip().lower()
        if not name:
            return None
        import sounddevice as sd
        cands = [(i, d) for i, d in enumerate(sd.query_devices()) if d["max_output_channels"] > 0 and name in d["name"].lower()]
        mme = [i for i, d in cands if sd.query_hostapis(d["hostapi"])["name"] == sd.query_hostapis(0)["name"]]
        return (mme or [i for i, _ in cands] or [None])[0]

    def play(self, audio, sr):
        import sounddevice as sd
        self._stop.clear()
        cb, self.first_cb = getattr(self, "first_cb", None), None
        if cb:
            try: cb()
            except Exception: pass
        f = audio.astype(np.float32) / 32768.0
        try:
            from . import modes
            f = f * modes.volume()  # BLACK / Stealth: quieter voice
        except Exception: pass
        f = np.concatenate([np.zeros(int(sr * 0.05), np.float32), f, np.zeros(int(sr * 0.1), np.float32)])
        hop = int(sr * 0.05)
        env = [float(np.sqrt(np.mean(f[i:i + hop] ** 2))) for i in range(0, len(f), hop)]
        peak = max(env + [1e-4])
        dev = None
        try: dev = self.out_device()
        except Exception: log.exception("output device")
        try:
            sd.play(f, sr, device=dev)
        except Exception:
            log.exception("play on %s failed; using default", dev); sd.play(f, sr)
        t0 = time.time()
        dur = len(f) / sr
        while time.time() - t0 < dur:
            if self._stop.is_set():
                sd.stop(); break
            i = int((time.time() - t0) / 0.05)
            self.level_cb(min(1.0, env[min(i, len(env) - 1)] / peak))
            time.sleep(0.03)
        sd.wait()
        self.level_cb(0.0)


# name -> settings applied when picked in Settings
VOICE_PRESETS = {
    "edge_ryan":    {"label": "Ryan (British, calm) - online", "tts_engine": "edge", "edge_voice": "en-GB-RyanNeural"},
    "edge_thomas":  {"label": "Thomas (British, crisp) - online", "tts_engine": "edge", "edge_voice": "en-GB-ThomasNeural"},
    "edge_sonia":   {"label": "Sonia (British) - online", "tts_engine": "edge", "edge_voice": "en-GB-SoniaNeural"},
    "edge_guy":     {"label": "Guy (American) - online", "tts_engine": "edge", "edge_voice": "en-US-GuyNeural"},
    "edge_aria":    {"label": "Aria (American) - online", "tts_engine": "edge", "edge_voice": "en-US-AriaNeural"},
    "windows":      {"label": "Windows voice - offline, nothing sent", "tts_engine": "windows"},
}


def apply_preset(name):
    p = VOICE_PRESETS.get(name)
    if p:
        config.save({k: v for k, v in p.items() if k != "label"} | {"voice_preset": name})
