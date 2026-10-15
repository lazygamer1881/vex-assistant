"""Settings for Vex. Stored as JSON in <install>/settings.json."""
import json, os, copy, threading

APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # VexAssistant/
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
MODELS_DIR = os.path.join(APP_DIR, "models")
LOG_DIR = os.path.join(APP_DIR, "logs")

LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
PROGRAMFILES = os.environ.get("ProgramFiles", r"C:\Program Files")
USERPROFILE = os.environ.get("USERPROFILE", "")

DEFAULTS = {
    "assistant_name": "Vex",
    # Say any of these to wake Vex. Words must be common English words (Vex checks this in Settings).
    "wake_phrases": ["hey vex", "wake up"],
    "user_name": "",
    "address": "sir",                # how the assistant addresses you: sir / maam / name / none
    "greeting": "",                   # blank = rotate butler greetings
    "follow_up_seconds": 8,          # after a reply, keep listening this long without the wake phrase
    "listening_enabled": True,       # always-listening for the wake phrase
    "push_to_talk_hotkey": "ctrl+alt+v",
    "stop_hotkey": "ctrl+alt+x",     # instantly cancels whatever Vex is doing (same as saying "Vex stop")
    "kill_phrases": ["vex stop", "stop stop"],
    "speaker_device": "",            # output device name ("" = Windows default)
    "mic_device": None,              # None = Windows default mic
    "speech_sensitivity": 0.012,     # RMS level counted as speech (lower = more sensitive)
    "mic_autocal": True,             # 4.2: measure room noise when the mic opens
    "mic_agc": True,                 # 4.2: auto level - boosts quiet speech for the wake word / Whisper (in memory only)
    "mic_max_gain": 4.0,
    "noise_gate": True,              # 4.2: soft gate for steady background hum
    "stream_replies": True,
    "endpoint_blocks": 6,            # 4.2 speed: stop recording after 0.6 s of silence (was 0.8 s)          # 4.2: speak answers sentence by sentence while they're still generating
    # Speech to text
    "whisper_model": "base.en",      # base.en (fast) or small.en (more accurate, bigger)
    "whisper_device": "auto",        # auto / cuda / cpu
    "whisper_compute": "int8",       # CPU math: int8 (fastest) or float32 (if int8 gives junk text)
    # Brain
    "llm_backend": "ollama",         # ollama or openai_compatible
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "qwen2.5:7b",          # big model for hard questions (optional)
    "ollama_model_light": "qwen2.5:3b",
    "ollama_fast_model": "qwen2.5:3b",    # 4.2 speed: small model kept loaded forever for quick chat/commands
    "route_hard": True,                   # 4.2: hard questions (explain / homework / code / long) go to ollama_model
    "llm_ctx": 4096,                      # one context size everywhere so Ollama never reloads the model
    "vision_model": "moondream",
    "youtube_handle": "",
    "barge_in": True,
    "fullscreen": False,
    "start_view": "ai",
    "start_page": "",                 # page to open on launch ("" = home)
    "hand_control_remember": False,   # False: hand control/camera always starts OFF on launch
    "look": {},                       # self-customization (whitelisted theme vars, see look.py)
    "hard_provider": "",              # route hard questions to this agent ("" = same brain)
    "openrouter_key": "", "openrouter_model": "openrouter/auto",
    "lmstudio_enabled": False, "lmstudio_url": "http://127.0.0.1:1234/v1", "lmstudio_model": "local-model",
    "agent_webhook_url": "", "webhook_key": "",
    "discord_webhook_url": "",
    "accounts": {},                   # {"spotify": {"client_id": ...}} - tokens live in the DPAPI vault
    "display_mode": "ondemand",           # ondemand (other monitor only used briefly when needed) | single (never) | span (always-on HUD)
    "main_monitor": 1,                # 1-based, left to right
    "hud_clickthrough": True,
    "ui_sounds": False, "mode": "blue",                # subtle original UI blips (synthesised, toggle in Settings or "sound effects off")
    "brief_on_wake": True,            # 4.0 briefing cards after the boot cinematic
    "boot_cinematic": True,           # 4.0 rings-assemble boot (skippable: click / any key / Esc)
    "idle_wallpaper": True,           # 4.0 calm live-wallpaper look after wallpaper_idle_min of no input
    "wallpaper_idle_min": 10,
    "setup_done": False,
    "intro_on": True,                 # 4.0 intro presentation on startup
    "intro_freq": "day",              # "day" = first launch of the day, "every" = every launch
    "intro_last": "",              # 4.0 first-run wizard
    "smart_home": {"enabled": False, "mode_lights": False},
    "boot_voice": True,               # "All systems online" on launch
    "demo_seq": [],                   # one-shot test sequence ["seconds|command", ...] (then cleared)
    "demo_protocol": "",              # one-shot: run "<colour> protocol" once ~15s after launch (then cleared)
    "hud_style": "compact",           # compact (corner column) | terminal (full-monitor dense dashboard)               # dashboard on launch: "ai" (orb only, unfold on command) or "full"
    "hand_control": False,            # webcam hand gestures (camera only runs while on; frames never saved or sent)
    "hand_camera": "",                # webcam deviceId ("" = first camera)
    "hand_mouse": False,              # gestures also drive the real Windows mouse (default: dashboard only)
    "ui_motion": "full",              # dashboard animation: full | auto (follow Windows "Animation effects") | reduced
    "embed_model": "nomic-embed-text",
    "index_extra_roots": [],
    "start_ollama_automatically": True,
    "api_base_url": "",              # optional, e.g. https://api.openai.com/v1 (not required)
    "api_key": "",                   # optional - leave blank to stay 100% local
    "api_model": "",
    # Voice
    "tts_engine": "edge",            # edge (online, free) -> piper (offline) -> windows (built-in)
    "edge_voice": "en-GB-RyanNeural",   # calm British butler (default since 2.1)
    "voice_style": "butler", "voice_human": True, "voice_rate": "-1%", "voice_pitch": "-4Hz",
    "voice_preset": "edge_ryan",
    "kokoro_voice": "bm_george:0.6,bm_lewis:0.4", "kokoro_speed": 0.86,      # see VOICE_PRESETS in tts.py
    "voice_fx": False,               # subtle reverb / AI polish
    "butler_rate": "-8%", "butler_pitch": "-5Hz",         # butler / casual
    "piper_voice_gb": "en_GB-alan-medium",
    "edge_rate": "+8%",
    "piper_voice": "en_US-ryan-medium",
    "volume_step": 5,                # number of volume key presses per "volume up/down" (2% each)
    # Streaming
    "streamlabs_api_token": "",      # Streamlabs Desktop > Settings > Remote Control > show details > API token
    "streamlabs_port": 59650,
    "obs_websocket_password": "",
    "obs_websocket_port": 4455,
    "starting_scene": "Starting Soon",
    "stream_setup_shortcut": "",     # auto-detected (Start Stream.lnk) if blank
    "proactive_trending": False,      # on the first wake of the day, mention a trending Steam game
    "youtube_channel_url": "",
    "twitch_url": "https://www.twitch.tv",
    # App
    "start_with_windows": False,
    "update_url": "",                # 4.3: public JSON file to check for new versions ("" = update checks off)
    "weather_auto_location": False,  # 4.3: only guess the city from your internet address if you turn this on
    "keep_model_warm": True,         # keep the AI model loaded on the GPU so wakes are instant...
    "game_mode_processes": ["Gorilla Tag.exe", "vrserver.exe"],  # ...but free the GPU while these run (model runs on CPU instead)
    "min_free_vram_mb": 3000,        # only hold the model on the GPU if at least this much VRAM is free
    "close_to_tray": True,
    # Vex 2.0 assistant
    "brain": "auto",                 # auto (cloud if a key is set, else local) / local / groq / gemini / openai / anthropic
    "groq_key": "", "groq_model": "llama-3.3-70b-versatile",
    "gemini_key": "", "gemini_model": "gemini-2.5-flash",
    "openai_key": "", "openai_model": "gpt-4o-mini",
    "anthropic_key": "", "anthropic_model": "claude-haiku-4-5",
    "weather_city": "",          # blank = guess from internet location
    "units": "imperial",             # imperial / metric
    "morning_briefing": False,       # off by default
    "briefing_time": "07:30",
    "briefing_on_unlock": False,      # brief on the first unlock each morning (off by default)
    # Smart home (optional, safe to leave blank)
    "hue_bridge_ip": "", "hue_username": "",
    "ha_url": "", "ha_token": "",
    "extra_apps": {},
    # Phone bridge (iPhone Shortcut / phone web app on the home Wi-Fi)
    "phone_enabled": False,          # off until you turn it on in Settings > Phone
    "ntfy_topic": "",                # your own private ntfy.sh topic; phone pushes stay off until you set one
    "conversation_mode": True,
    "proactive_alerts": True, "proactive_voice": True, "quiet_start": 23, "quiet_end": 7, "low_disk_gb": 15, "focus_until": 0,       # after the wake phrase, keep listening until "that's all"
    "conversation_timeout_s": 600,   # ...or until this long with no speech
    "phone_port": 8765,
    "phone_key": "",                 # pairing key, made on first start; shown in Settings > Phone                # "name": "path or url" - extra things Vex can open
}

_lock = threading.Lock()
_settings = None


def load():
    global _settings
    with _lock:
        data = copy.deepcopy(DEFAULTS)
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
                user = json.load(f)
            if isinstance(user, dict):
                data.update({k: v for k, v in user.items() if k in DEFAULTS})
        except FileNotFoundError:
            pass
        except Exception:
            pass
        _settings = data
        return data


VIEW = {"mode": "ai", "seq": 0}   # dashboard view requested by voice: "ai" (orb only) or "full"


def set_view(mode):
    VIEW["mode"] = mode; VIEW["seq"] += 1


SECRET_KEYS = {"api_key", "groq_key", "gemini_key", "openai_key", "anthropic_key", "openrouter_key", "webhook_key", "discord_webhook_url",
               "streamlabs_api_token", "obs_websocket_password", "ha_token", "hue_username"}


def _migrate_secrets():
    """Move any plaintext keys from settings.json into the DPAPI vault (once)."""
    try:
        from . import vault
        moved = False
        for k in SECRET_KEYS:
            v = _settings.get(k)
            if v:
                vault.put(k, v); _settings[k] = ""; moved = True
        if moved:
            save({})
    except Exception:
        import logging; logging.exception("vault migrate")


def get(key=None, default=None):
    if _settings is None:
        load()
        _migrate_secrets()
    if key in SECRET_KEYS:
        try:
            from . import vault
            return vault.get(key) or _settings.get(key) or ""
        except Exception:
            return _settings.get(key) or ""
    return _settings if key is None else _settings.get(key, DEFAULTS.get(key, default))


def save(updates: dict):
    if _settings is None:
        load()
    updates = dict(updates or {})
    for k in [k for k in updates if k in SECRET_KEYS]:
        from . import vault
        vault.put(k, updates.pop(k) or "")
        _settings[k] = ""
    with _lock:
        for k, v in (updates or {}).items():
            if k in DEFAULTS:
                _settings[k] = v
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_settings, f, indent=2)
        os.replace(tmp, SETTINGS_PATH)
    return _settings


def public():
    """Settings for the UI (hides the secret values but says if they are set)."""
    s = dict(get())
    for k in SECRET_KEYS:
        s[k + "_set"] = bool(get(k))
        s[k] = ""
    s.pop("phone_key", None)  # shown only through the Phone section
    return s


# ---------------- public build: the assistant's name and how it addresses you, applied to everything it says/shows
import re as _re


def assistant():
    return (get("assistant_name") or "Vex").strip() or "Vex"


def brand(s):
    if not isinstance(s, str) or not s:
        return s
    n = assistant()
    if n != "Vex":
        s = _re.sub(r"\bVEX\b", n.upper(), s)
        s = _re.sub(r"\bVex\b", n, s)
        s = _re.sub(r"(?<![\w./\\-])vex(?![\w./\\-])", n.lower(), s)
    a = (get("address") or "sir").lower()
    if a in ("maam", "ma'am"):
        s = _re.sub(r"\bsir\b", "ma'am", s); s = _re.sub(r"\bSir\b", "Ma'am", s)
    elif a in ("name", "none"):
        who = (get("user_name") or "").strip() if a == "name" else ""
        if who:
            s = _re.sub(r"\bsir\b", who, s); s = _re.sub(r"\bSir\b", who, s)
        else:
            s = _re.sub(r",\s*sir\b", "", s); s = _re.sub(r"\bSir,\s*", "", s); s = _re.sub(r"\s+sir\b", "", s)
    return s


def apply_names(assistant_name=None):
    """Wake/stop phrases follow the assistant's name ('hey nova', 'nova stop')."""
    n = (assistant_name or assistant()).strip().lower()
    w = [p for p in (get("wake_phrases") or []) if not _re.match(r"(?:hey|yo) ", p) and p != "wake up"]
    return {"wake_phrases": [f"hey {n}", "wake up"] + w, "kill_phrases": [f"{n} stop", "stop stop"]}


def write_ui_brand():
    """ui/brand_cfg.js: the name the UI shows (wordmark, intro, titles)."""
    import json as _j
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "brand_cfg.js")
        with open(p, "w", encoding="utf-8") as f:
            f.write("window.__AN=%s;window.__UN=%s;\n" % (_j.dumps(assistant()), _j.dumps(get("user_name") or "")))
    except Exception:
        pass
