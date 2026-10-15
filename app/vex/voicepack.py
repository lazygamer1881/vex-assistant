"""4.3: the voice pack (speech recognition), downloaded on first run instead of bundled in the installer.

Everything comes from the official source of each part and is checked against a pinned SHA-256 before use:
  * Python wheels (ctranslate2, tokenizers, onnxruntime, vosk) from PyPI (files.pythonhosted.org)
  * Whisper base.en speech model from Hugging Face (Systran/faster-whisper-base.en, fixed revision)
  * Vosk small English wake-word model from alphacephei.com
Wheels are unpacked into <install>/voicepack/site (no pip, nothing outside the install folder).
Nothing about you is sent: these are plain file downloads."""
import os, sys, io, json, time, hashlib, zipfile, shutil, threading, logging, urllib.request
from . import config

log = logging.getLogger("vex.voicepack")
PACK_DIR = os.path.join(config.APP_DIR, "voicepack")
SITE = os.path.join(PACK_DIR, "site")
DL = os.path.join(PACK_DIR, "downloads")
_PY = "https://files.pythonhosted.org/packages/"
_HF = "https://huggingface.co/Systran/faster-whisper-base.en/resolve/3d3d5dee26484f91867d81cb899cfcf72b96be6c/"
WHEELS = [
    ("ctranslate2", _PY + "4e/23/e3b5322ff7368fcbed181ea4c209149416e7940b5b04971d5ee4084afe1a/ctranslate2-4.8.2-cp312-cp312-win_amd64.whl",
     19222069, "d94421d565d0de61c032998f737a18942b0f2bef40c0424b1846ec6f67300105"),
    ("tokenizers", _PY + "db/f7/0a69ac6b82dbccf3f71add938a161c497952749294b8dd6dfe03a819dc40/tokenizers-0.23.2-cp310-abi3-win_amd64.whl",
     2863236, "2e96f5699d5249c9c64aa8412e044f727aae3a4098cf830f9901ec1afc361cde"),
    ("onnxruntime", _PY + "a6/13/0f1699f6de549c9324bc9112a2a85b14c517904cd11b562a654643b755a1/onnxruntime-1.30.0-cp312-cp312-win_amd64.whl",
     14311470, "f3501472571f1b1eee50e017851e7929f5ea37312d2d8c2494a19e8fc58b4a38"),
    ("vosk", _PY + "c0/4c/deb0861f7da9696f8a255f1731bb73e9412cca29c4b3888a3fcb2a930a59/vosk-0.3.45-py3-none-win_amd64.whl",
     13997596, "6994ddc68556c7e5730c3b6f6bad13320e3519b13ce3ed2aa25a86724e7c10ac"),
]
WHISPER = [
    ("config.json", 2227, "f3bc3821e9fc76a27bae538e11ae5b677dcdd352b4600429ce7951d398569aeb"),
    ("model.bin", 145216508, "2a166925539a16005f14ff328359f9b9adb9dc4fb631bb3b227526862e93e2ef"),
    ("tokenizer.json", 2128466, "929c5252409436dce1b38a75d1abbcb5e132d170d8e324e4e04ed915fa2d22df"),
    ("vocabulary.txt", 422309, "ff77588746d3a2595d32ab5b69ffd7b95ce2441ac57533cb66fc3eb575a115cf"),
]
VOSK_NAME = "vosk-model-small-en-us-0.15"
VOSK = ("https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip", 41205931,
        "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498")
TOTAL = sum(w[2] for w in WHEELS) + sum(w[1] for w in WHISPER) + VOSK[1]
STATE = {"running": False, "done": False, "error": "", "pct": 0, "got": 0, "total": TOTAL, "part": "", "restart": False}


def activate():
    """Called at startup: makes an installed voice pack importable."""
    if os.path.isdir(SITE) and SITE not in sys.path:
        sys.path.insert(0, SITE)
        try:
            os.add_dll_directory(SITE)
        except Exception:
            pass


def whisper_dir():
    return os.path.join(config.MODELS_DIR, "whisper", "base.en")


def _can_import(mod):
    import importlib.util
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def _whisper_model_present():
    if os.path.isfile(os.path.join(whisper_dir(), "model.bin")):
        return True
    root = os.path.join(config.MODELS_DIR, "whisper")
    for dp, dn, fn in os.walk(root):           # Hugging Face cache layout (older installs)
        if "model.bin" in fn and "base.en" in dp.replace("\\", "/"):
            return True
    return False


def status():
    libs = {n: _can_import(n) for n in ("ctranslate2", "tokenizers", "onnxruntime", "vosk")}
    models = {"whisper": _whisper_model_present(), "wake": os.path.isdir(os.path.join(config.MODELS_DIR, VOSK_NAME))}
    ready = all(libs.values()) and all(models.values())
    return {"ready": ready, "libs": libs, "models": models, "size_mb": round(TOTAL / 1e6), **{"job": dict(STATE)}}


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _fetch(url, dest, size, sha, label):
    """Downloads with resume, then verifies the SHA-256. A mismatch deletes the file and stops."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) == size and _sha(dest) == sha:
        STATE["got"] += size
        return dest
    part = dest + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if have > size:
        os.remove(part); have = 0
    base = STATE["got"]
    STATE["part"] = label
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VexAssistant-setup", **({"Range": f"bytes={have}-"} if have else {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                if have and r.status != 206:
                    have = 0
                with open(part, "ab" if have else "wb") as f:
                    while True:
                        if STATE.get("cancel"):
                            raise RuntimeError("cancelled")
                        b = r.read(1 << 16)
                        if not b:
                            break
                        f.write(b); have += len(b)
                        STATE["got"] = base + have
                        STATE["pct"] = int(100 * STATE["got"] / TOTAL)
            break
        except Exception as e:
            if str(e) == "cancelled" or attempt == 3:
                raise
            log.info("download %s retry: %s", label, e)
            time.sleep(2 + attempt * 3)
            have = os.path.getsize(part) if os.path.exists(part) else 0
    if os.path.getsize(part) != size or _sha(part) != sha:
        os.remove(part)
        raise RuntimeError(f"{label}: download didn't match its checksum, so it was deleted. Please try again.")
    os.replace(part, dest)
    STATE["got"] = base + size
    return dest


def _unpack_wheel(path):
    with zipfile.ZipFile(path) as z:
        for m in z.infolist():
            n = m.filename.replace("\\", "/")
            if n.startswith("/") or ".." in n.split("/") or ":" in n:
                raise RuntimeError("unsafe file name in wheel")
            parts = n.split("/")
            if len(parts) > 2 and parts[0].endswith(".data") and parts[1] == "scripts":
                continue           # console scripts aren't needed
            z.extract(m, SITE)


def _run():
    try:
        os.makedirs(SITE, exist_ok=True)
        for name, url, size, sha in WHEELS:
            p = _fetch(url, os.path.join(DL, url.rsplit("/", 1)[1]), size, sha, f"{name} (speech engine)")
            STATE["part"] = f"installing {name}"
            _unpack_wheel(p)
        wd = whisper_dir()
        for fn, size, sha in WHISPER:
            _fetch(_HF + fn, os.path.join(wd, fn), size, sha, f"speech model · {fn}")
        if not os.path.isdir(os.path.join(config.MODELS_DIR, VOSK_NAME)):
            z = _fetch(VOSK[0], os.path.join(DL, VOSK_NAME + ".zip"), VOSK[1], VOSK[2], "wake-word model")
            STATE["part"] = "unpacking wake-word model"
            with zipfile.ZipFile(z) as zf:
                for m in zf.infolist():
                    n = m.filename.replace("\\", "/")
                    if n.startswith("/") or ".." in n.split("/") or not n.startswith(VOSK_NAME + "/"):
                        raise RuntimeError("unsafe file name in model zip")
                zf.extractall(config.MODELS_DIR)
        else:
            STATE["got"] += VOSK[1]
        shutil.rmtree(DL, ignore_errors=True)       # keep only what's needed
        activate()
        STATE.update(done=True, running=False, pct=100, part="ready", restart=True)
        log.info("voice pack installed")
    except Exception as e:
        log.warning("voice pack: %s", e)
        STATE.update(running=False, error=str(e)[:200])


def install():
    """Starts the download in the background (the user clicked the button). Safe to call twice."""
    if STATE["running"]:
        return status()
    if status()["ready"]:
        STATE.update(done=True, pct=100, part="ready")
        return status()
    STATE.update(running=True, done=False, error="", pct=0, got=0, part="starting", cancel=False)
    threading.Thread(target=_run, daemon=True, name="voicepack").start()
    return status()


def cancel():
    STATE["cancel"] = True
    return status()
