"""4.3: permissions page, crash report / update helpers, speaker test, Ollama auto-setup, restart."""
import os, re, sys, json, time, threading, subprocess, logging, urllib.request
from . import config

log = logging.getLogger("vex.v43")

# Each switch the user can flip, with what it does in plain words. Defaults are the safe choice.
PERMS = [
    ("listening_enabled", "Microphone · wake word", "Listens for the wake phrase on this PC. Speech is turned into text in memory and thrown away; audio is never saved or sent."),
    ("hand_control", "Camera · hand control", "Uses the webcam to follow hand gestures. Off by default. Frames stay in memory, never saved or sent."),
    ("online_voice", "Online voice (Microsoft neural voice)", "Sends the words the assistant says (not your voice) to Microsoft's speech service to make natural audio. Off = offline Windows voice."),
    ("phone_enabled", "Phone notifications & phone remote", "Off by default. When on, pushes go only to your own private ntfy topic, and the phone page needs a pairing key."),
    ("weather_auto_location", "Guess my city for weather", "Off by default. When on and no city is set, looks up your rough location from your internet address (ip-api.com)."),
    ("proactive_trending", "Game suggestions", "Off by default. Checks Steam's public store for trending games to suggest."),
    ("ui_sounds", "UI sound effects", "Small synthesized sounds for clicks and wake. Off by default."),
    ("start_with_windows", "Start with Windows", "Opens the assistant quietly when you sign in. Off by default."),
]
ALWAYS_ASKS = ["Shutting down, restarting, signing out or sleeping the PC", "Deleting or moving files (to the Recycle Bin)",
               "Sending or posting anything (messages, Discord, pressing Enter in a chat)", "Running programs, scripts or PowerShell commands that change things",
               "Closing windows that may have unsaved work", "Running Python code it wrote"]
NEVER = ["Never records, saves or uploads your voice or camera", "No analytics, tracking or hidden data collection: no account, no ID, no usage stats",
         "Never signs in to your accounts or reads saved passwords", "Never starts a stream or recording unless you ask",
         "API keys you add are encrypted with Windows (DPAPI) and only sent to the AI service you picked"]


def _get(k):
    if k == "online_voice":
        return (config.get("tts_engine") or "edge") in ("edge", "kokoro")
    if k == "start_with_windows":
        try:
            from . import main as m; return bool(m.is_start_with_windows())
        except Exception:
            return False
    return bool(config.get(k))


def perms():
    from . import updatecheck, crashreport
    return {"perms": [{"k": k, "label": l, "desc": d, "on": _get(k)} for k, l, d in PERMS], "asks": ALWAYS_ASKS, "never": NEVER,
            "update_url": config.get("update_url") or "", "crash": crashreport.info(),
            "ntfy": bool((config.get("ntfy_topic") or "").strip())}


def perm_set(k, on):
    on = bool(on)
    if k not in {p[0] for p in PERMS}:
        return perms()
    if k == "online_voice":
        config.save({"tts_engine": "edge" if on else "windows"})
    elif k == "start_with_windows":
        try:
            from . import main as m; m.set_start_with_windows(on)
        except Exception as e:
            log.info("startup toggle: %s", e)
    elif k == "listening_enabled":
        config.save({k: on})
        try:
            from . import product
            a = product._app(); a.vex.listener.enabled = on
        except Exception:
            pass
    else:
        config.save({k: on})
    return perms()


# ---------------- crash report
def crash_open():
    from . import crashreport
    i = crashreport.info()
    try:
        if i["exists"]:
            subprocess.Popen(["explorer", "/select,", i["path"]])
        else:
            os.startfile(os.path.dirname(i["path"]))
    except Exception as e:
        return {"ok": False, "msg": str(e)}
    return {"ok": True}


def crash_copy():
    from . import crashreport
    t = crashreport.text()
    try:
        subprocess.run(["clip"], input=t.encode("utf-16le"), creationflags=0x08000000, timeout=10)
        return {"ok": True, "chars": len(t)}
    except Exception as e:
        return {"ok": False, "msg": str(e), "text": t}


# ---------------- speaker test
def speaker_test(vex):
    try:
        n = config.get("assistant_name") or "Vex"
        threading.Thread(target=lambda: vex.say(f"Testing, testing. This is {n}. If you can hear me, your speakers are set."), daemon=True).start()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


# ---------------- Ollama auto-setup: official installer, signature checked before it runs
OLLAMA_URL = "https://ollama.com/download/OllamaSetup.exe"
OL = {"running": False, "pct": 0, "got": 0, "total": 0, "stage": "", "error": "", "launched": False}


def _setup_path():
    return os.path.join(config.APP_DIR, "cache", "OllamaSetup.exe")


def _signature_ok(path):
    """Windows Authenticode check: must be validly signed and the signer must be Ollama."""
    ps = ("$s=Get-AuthenticodeSignature -LiteralPath $env:VEX_OLS; "
          "[pscustomobject]@{st=[string]$s.Status;sub=[string]$s.SignerCertificate.Subject}|ConvertTo-Json -Compress")
    env = dict(os.environ, VEX_OLS=path)
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, text=True, env=env,
                       timeout=120, creationflags=0x08000000)
    try:
        j = json.loads(r.stdout.strip() or "{}")
    except Exception:
        j = {}
    ok = j.get("st") == "Valid" and re.search(r"\bO=\"?Ollama", j.get("sub", ""), re.I) is not None
    return ok, j


def _ollama_job():
    p = _setup_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        OL.update(stage="downloading")
        req = urllib.request.Request(OLLAMA_URL, headers={"User-Agent": "VexAssistant-setup"})
        with urllib.request.urlopen(req, timeout=60) as r, open(p + ".part", "wb") as f:
            OL["total"] = int(r.headers.get("Content-Length") or 0)
            while True:
                if OL.get("cancel"):
                    raise RuntimeError("cancelled")
                b = r.read(1 << 17)
                if not b:
                    break
                f.write(b); OL["got"] += len(b)
                if OL["total"]:
                    OL["pct"] = int(100 * OL["got"] / OL["total"])
        os.replace(p + ".part", p)
        OL.update(stage="checking signature")
        ok, info = _signature_ok(p)
        if not ok:
            os.remove(p)
            raise RuntimeError(f"The download's digital signature didn't check out ({info.get('st') or 'unknown'}), so it was deleted.")
        OL.update(stage="installer open: follow the Ollama setup window")
        os.startfile(p)       # Ollama's own installer window; the user clicks through it
        OL.update(launched=True, running=False)
    except Exception as e:
        try:
            if os.path.exists(p + ".part"): os.remove(p + ".part")
        except Exception:
            pass
        OL.update(running=False, error=str(e)[:200], stage="")


def _ollama_exe():
    import shutil
    for p in (shutil.which("ollama"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
              os.path.join(config.APP_DIR, "ollama", "ollama.exe")):
        if p and os.path.exists(p):
            return p
    return None


def ollama_install():
    if _ollama_exe():
        return {"installed": True, **OL}
    if not OL["running"]:
        OL.update(running=True, pct=0, got=0, total=0, error="", launched=False, cancel=False)
        threading.Thread(target=_ollama_job, daemon=True, name="ollama-setup").start()
    return dict(OL)


def ollama_job():
    d = dict(OL); d["installed"] = bool(_ollama_exe())
    if d["installed"] and not OL["running"]:
        try:
            if os.path.exists(_setup_path()): os.remove(_setup_path())   # tidy up once Ollama is installed
        except Exception:
            pass
    return d


# ---------------- restart (after the voice pack)
def restart(app):
    def go():
        time.sleep(0.8)
        try:
            if getattr(app, "tray", None): app.tray.stop()
        except Exception:
            pass
        os._exit(75)          # the watchdog sees 75 and starts a fresh, visible copy
    threading.Thread(target=go, daemon=True).start()
    return {"ok": True}
