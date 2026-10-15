"""Speech to text with faster-whisper (CUDA if it works, otherwise CPU int8)."""
import os, logging, threading
import numpy as np
from . import config

log = logging.getLogger("vex.stt")
PROMPT = ("Vex, Discord, Steam, Minecraft, Roblox, YouTube, Twitch, OBS, Spotify, Chrome, "
          "set a timer, what's the weather, open my downloads folder.")


class STT:
    def __init__(self):
        self.model = None
        self.device = "?"
        self._lock = threading.Lock()

    def load(self):
        try:
            import av  # noqa: F401  (only used by faster-whisper to decode files; Vex feeds raw audio)
        except Exception:
            import sys, types
            sys.modules.setdefault("av", types.ModuleType("av"))
        from faster_whisper import WhisperModel
        name = config.get("whisper_model") or "base.en"
        root = os.path.join(config.MODELS_DIR, "whisper")
        local = os.path.join(root, name)
        if os.path.isfile(os.path.join(local, "model.bin")):
            name = local      # 4.3: voice-pack layout (models/whisper/base.en/model.bin), no Hugging Face cache needed
        want = config.get("whisper_device") or "auto"
        tries = []
        if want in ("auto", "cuda"):
            tries.append(("cuda", "float16"))
        if want in ("auto", "cpu") or not tries:
            tries.append(("cpu", config.get("whisper_compute") or "int8"))
        last = None
        for dev, ct in tries:
            try:
                m = WhisperModel(name, device=dev, compute_type=ct, download_root=root, cpu_threads=max(4, min(8, (os.cpu_count() or 8) // 2)))
                # make sure the device actually runs (CUDA can load but fail without cuBLAS/cuDNN)
                list(m.transcribe(np.zeros(16000, dtype=np.float32), language="en", beam_size=1)[0])
                self.model, self.device = m, f"{dev} ({os.path.basename(name)})"
                log.info("whisper on %s", self.device)
                return self.device
            except Exception as e:
                last = e
                log.info("whisper %s failed: %s", dev, e)
        raise RuntimeError(f"whisper failed to load: {last}")

    def transcribe(self, audio_f32):
        if self.model is None:
            self.load()
        with self._lock:
            kw = dict(language="en", beam_size=1, best_of=1, temperature=0.0, initial_prompt=PROMPT.replace("Vex,", config.assistant() + ",", 1), condition_on_previous_text=False,
                      without_timestamps=True, no_speech_threshold=0.6)
            if getattr(self, "vad_ok", True):
                kw.update(vad_filter=True, vad_parameters={"min_silence_duration_ms": 300, "speech_pad_ms": 200})
            try:
                segs, _ = self.model.transcribe(audio_f32, **kw)
                segs = list(segs)
            except Exception as e:
                if not kw.get("vad_filter"):
                    raise
                log.info("whisper VAD unavailable (%s), transcribing without it", e)
                self.vad_ok = False
                kw.pop("vad_filter", None); kw.pop("vad_parameters", None)
                segs = list(self.model.transcribe(audio_f32, **kw)[0])
            text = " ".join(s.text.strip() for s in segs if s.no_speech_prob < 0.8).strip()
        junk = {"thank you.", "thanks for watching!", "you", "thank you", ".", "bye.", "thanks for watching."}
        return "" if text.lower() in junk else text
