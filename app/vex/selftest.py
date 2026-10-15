"""Headless self test: no mic, no window, nothing gets opened/locked/typed (tools run in dry-run)."""
import os, sys, json, time, shutil, wave, traceback
import numpy as np
from . import config, tools, winutil


def _resample(a, sr, to=16000):
    n = int(len(a) * to / sr)
    return np.interp(np.linspace(0, len(a), n, endpoint=False), np.arange(len(a)), a).astype(np.float32)


def run():
    R = {}
    out = os.path.join(config.LOG_DIR, "selftest")
    os.makedirs(out, exist_ok=True)
    def step(name, fn):
        t0 = time.time()
        try:
            R[name] = {"ok": True, "result": fn(), "sec": round(time.time() - t0, 2)}
        except Exception as e:
            R[name] = {"ok": False, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-800:], "sec": round(time.time() - t0, 2)}
        print(name, "OK" if R[name]["ok"] else "FAIL", R[name].get("result", R[name].get("error")), flush=True)

    tools.DRY_RUN = True
    from . import actlog
    actlog.LOG_PATH = os.path.join(out, "actions-selftest.log")  # keep test entries out of the real actions.log
    if os.path.exists(actlog.LOG_PATH):
        os.remove(actlog.LOG_PATH)
    from .tts import TTS
    tts = TTS()
    clips = {}

    def tts_engine(eng):
        def f():
            fn = {"edge": tts._edge, "piper": tts._piper_synth, "windows": tts._windows}[eng]
            a, sr = fn("Bet, opening Steam and Discord.")
            p = os.path.join(out, f"voice_{eng}.wav")
            with wave.open(p, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(a.tobytes())
            clips[eng] = (a, sr)
            return f"{len(a)/sr:.1f}s -> {p}"
        return f
    for eng in ("edge", "windows"):
        step("tts_" + eng, tts_engine(eng))

    from .stt import STT
    stt = STT()
    step("stt_load", stt.load)

    def stt_test():
        src = clips.get("edge") or clips.get("piper") or clips.get("windows")
        a = _resample(src[0].astype(np.float32) / 32768.0, src[1])
        return stt.transcribe(a)
    step("stt_transcribe", stt_test)

    def wake_test():
        from vosk import Model, KaldiRecognizer, SetLogLevel
        from .listener import wake_match
        SetLogLevel(-1)
        m = Model(os.path.join(config.MODELS_DIR, "vosk-model-small-en-us-0.15"))
        res = {}
        for phrase in ("wake up", "hey vex", "open steam"):
            a, sr = tts._edge(phrase) if "edge" in clips else tts._windows(phrase)
            a16 = (_resample(a.astype(np.float32) / 32768.0, sr) * 32767).astype(np.int16)
            a16 = np.concatenate([np.zeros(8000, np.int16), a16, np.zeros(16000, np.int16)])
            rec = KaldiRecognizer(m, 16000)
            text = ""
            for i in range(0, len(a16), 1600):
                if rec.AcceptWaveform(a16[i:i + 1600].tobytes()):
                    text += json.loads(rec.Result()).get("text", "") + " "
            text += json.loads(rec.FinalResult()).get("text", "")
            res[phrase] = {"heard": text.strip(), "woke": bool(wake_match(text, config.get("wake_phrases")))}
        res["missing_words"] = [w for p in config.get("wake_phrases") for w in p.split() if m.vosk_model_find_word(w) < 0]
        return res
    step("wake_word", wake_test)

    from .brain import Brain
    from .core import ensure_ollama
    started = {"p": None}
    def ollama_test():
        started["p"] = ensure_ollama()
        b = Brain()
        b.keep_alive = -1  # don't shorten the running Vex's keep-warm setting
        import urllib.request
        with urllib.request.urlopen(config.get("ollama_url") + "/api/version", timeout=3) as r:
            ver = json.loads(r.read())
        t0 = time.time(); b.warmup(); warm = round(time.time() - t0, 1)
        out = {"version": ver, "warmup_s": warm}
        for q in ("yo what's up", "can you put my two windows next to each other", "pull up youtube studio for me"):
            t0 = time.time()
            content, calls = b._ollama([{"role": "system", "content": b._system()}, {"role": "user", "content": q}])
            out[q] = {"reply": content, "tool_calls": calls, "s": round(time.time() - t0, 1)}
        return out
    step("ollama", ollama_test)

    def rules_test():
        b = Brain()
        res = {}
        for q in ["open Steam and notify in Discord I'm going live in 5", "send", "split the windows", "lock my screen", "open streamlabs",
                  "open gorilla tag", "open quest link and steamvr", "open youtube studio and my channel", "switch to the starting soon scene",
                  "go live", "volume up", "what time is it", "set up my stream", "open capcut", "close discord", "go to sleep"]:
            r = b.handle(q)
            res[q] = r.get("say")
        return res
    step("commands_dry_run", rules_test)

    def pc_control_test():
        from . import pc
        b = Brain()
        b._llm = lambda raw: {"say": "<went to AI>"}
        convo = ["open my downloads folder", "open calculator", "open notepad", "open youtube.com", "find vex", "open it",
                 "minimize discord", "maximize this", "switch to steam", "show desktop", "close this window", "yes",
                 "type hello there", "press ctrl s", "hit alt tab", "press enter", "no",
                 "click", "double click", "right click at 500 300",
                 "take a screenshot", "pause the music", "next song", "previous song",
                 "how much disk space do I have", "what's my battery", "how much ram is free", "what's my gpu temp", "what's running",
                 "make a folder called vex test on my desktop", "move clip.mp4 to documents", "rename notes to old notes",
                 "delete vex test", "yes", "delete vex test", "no",
                 "shut down my pc", "vex stop", "yes", "restart the computer", "yeah do it", "sign me out", "nah",
                 "copy projects readme to desktop", "show me README in explorer",
                 "make a folder called vex test in program files", "yes", "find steam.exe in program files x86",
                 "move clip.mp4 to the d drive", "run powershell Get-PSDrive C", "run powershell Remove-Item C:\\Users\\Public\\nothing.txt", "no",
                 "run powershell Set-ItemProperty HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize -Name AppsUseLightTheme -Value 0", "vex stop"]
        res = []
        for q in convo:
            r = b.handle(q)
            res.append(f"{q!r} -> {r.get('say')!r}" + (" [WAITING FOR YES]" if r.get("confirm") else "") + (" [KILL]" if r.get("kill") else ""))
        ps = {c: ("never" if pc.NEVER_PS.search(c) else "read-only, runs" if pc.ps_is_read_only(c) else "asks (dangerous warning)" if pc.DANGER_PS.search(c) else "asks first") for c in [
            "Get-Process | Sort-Object CPU -Descending | Select -First 5", "Get-PSDrive C", "ipconfig", "Get-Service | Where Status -eq Running",
            "Remove-Item C:\\Users\\Public\\x.txt", "Set-ItemProperty HKCU:\\Software\\x -Name a -Value 1", "Stop-Process -Name chrome",
            "iex (irm http://x)", "Get-ChildItem C:\\Windows", "Get-Process; Stop-Process -Name x", "psexec cmd", "New-Item -ItemType File C:\\Users\\Public\\Desktop\\a.txt"]}
        w = {p_: (pc.protected_reason(p_) or "ok, no question") for p_ in [os.path.join(config.USERPROFILE, "Desktop", "x.txt"), os.path.join(pc.known_folders()["desktop"], "x"),
             r"C:\Windows\System32\x.dll", r"C:\Program Files\x", os.path.join(config.USERPROFILE, "AppData", "Roaming", "x"),
             os.path.join(config.APP_DIR, "app", "x.py"), pc.known_folders()["documents"], os.path.join(config.USERPROFILE, "Projects", "x.txt")]}
        return {"conversation": res, "powershell_rules": ps, "can_write": w, "start_menu_apps": len(pc.start_apps()),
                "log_lines": open(actlog.LOG_PATH, encoding="utf-8").read().count("\n")}
    step("pc_control_dry_run", pc_control_test)

    def env_test():
        apps = {k: (tools._first(v.get("exe", [])) or v.get("url")) for k, v in tools.app_table().items()}
        return {"apps": apps, "stream_setup": tools.find_stream_setup(), "windows_open": len(winutil.list_windows()),
                "trending_top3": [g["name"] for g in tools.trending_games()[:3]],
                "free_gb": round(shutil.disk_usage(config.APP_DIR).free / 1e9, 1)}
    step("environment", env_test)

    def mic_list():
        import sounddevice as sd
        return {"default_input": sd.query_devices(kind="input")["name"]}
    step("mic_detect_only", mic_list)

    if started["p"]:
        started["p"].terminate()
    with open(os.path.join(out, "selftest.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, default=str)
    print("SELFTEST DONE", sum(1 for v in R.values() if v["ok"]), "/", len(R))
