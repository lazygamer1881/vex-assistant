# Changelog

All notable changes to Vex Assistant. Newest first.

## 4.3.0 · Public Edition (2026-10-14)

### Smaller download
- Installer cut from 361 MB to the size listed in the release notes: the speech engine and AI models are no longer bundled.
- New **voice pack** (about 240 MB) downloads on first run, only when you click, from the official sources: PyPI (ctranslate2, tokenizers, onnxruntime, vosk), Hugging Face (Whisper base.en, fixed revision) and alphacephei.com (Vosk wake-word model). Every file is checked against a pinned SHA-256; a mismatch is deleted.
- Trimmed the bundled Python: removed unused libraries (video decoding, pip, Tk, test suites) and the GPL voice engines.
- The app starts and works by typing even before the voice pack is installed.

### First-run setup for everyone
- Name your assistant, choose how it addresses you, optional city for weather.
- Microphone level meter and a speaker test sound.
- Voice pack download with progress (keeps going in the background).
- Brain choice: **Set up Ollama for me** (downloads the official installer, checks its digital signature, opens it, then pulls the fast model) or **your own API key** (Groq, Gemini, OpenAI, Claude, OpenRouter) with a live test.
- Theme picker, intro settings (always skippable: click, Esc or say "skip"), and a plain-language privacy summary with an online/offline voice switch.
- "Skip setup and use defaults" on the first page.

### Safety and privacy
- New **Permissions** page (Settings › About › Permissions, or say "open permissions"): every switch in one place, safe defaults, plus the list of actions that always ask "Shall I proceed?".
- Weather no longer guesses your location from your internet address unless you turn that on.
- Phone notifications stay opt-in (your own private ntfy topic).
- No analytics, IDs or hidden network calls; the only automatic requests are the ones you trigger.
- Uninstaller now removes everything (program, voice pack, settings, memory, encrypted keys, logs, cache, shortcuts, startup entries).

### Reliability
- Local crash reports in `logs\crash-report.txt` with your user name and folders blanked out; open or copy them from Settings › About › Help & updates. Nothing is sent.
- Crash-proof startup: a startup failure shows a friendly message with the report location instead of silently closing.
- The watchdog records unexpected exits and restarts cleanly after the voice pack installs.
- Optional update check against a public version file (off until an address is set).

### Licensing
- MIT license for Vex Assistant; THIRD_PARTY_LICENSES.txt lists every bundled and downloaded component.

## 4.2.0

- Smarter, faster assistant: answers are spoken sentence by sentence while they're still being written; auto mic level, room-noise calibration and a soft noise gate for USB mics; the mic reconnects by itself if it drops or is replugged; sound-alike app matching for 'bring up'; older memories come back when they match what you ask; quick timers with labels and countdown chips, faster reminders; a 'what can you do' help card; a mic status dot on the HUD (level only, nothing recorded). Speed: a small fast model stays loaded for quick chat and the big one is used only for hard questions; shorter prompts; common commands answered instantly without the AI; faster speech recognition with voice detection; common phrases pre-voiced and speech generated in parallel. Typical reply now starts in about 2-3 s instead of ~1 minute. Dashboard tabs fixed: Home, System (gauges, top processes, drives, network), Activity (timeline) and Memory (search, add, delete) each have their own layout, with a clear active-tab bar and a smooth switch; works by mouse, hand swipe or voice ('show system tab').

## 4.1.0

- New startup presentation: cinematic letterbox, particle assembly of the core with a camera fly-through and depth of field, rings locking in with flash hits, 'VEX // SYSTEMS ONLINE' title card, kinetic briefing, fast-cut mode tour with a unique transition per mode, holographic scan across both monitors in sync, and a shockwave back to the AI-only core. ~52 s, no sounds, skippable.

## 4.0.0

- Product release: cinematic boot, startup intro presentation, briefing cards, subtle captions of Vex's replies, 'show me' glass panels, task step log, mini-orb, theme gallery, idle wallpaper, smart-home tiles (opt-in), setup wizard, About page, brand kit, Setup.exe, showcase mode. Core colour now follows every mode.

## 3.9.0

- Blueprint companion HUD on every other monitor; per-mode aesthetics.

## 3.8.0

- Abstract AI entity core (no face), blueprint layout, UI sounds off by default, more natural voice.

## 3.7.1

- Humanlike voice: contractions, warmer phrasing, natural pauses.

## 3.7.0

- Reactor HUD in the expanded view.

## 3.6.0

- Cinematic visuals: bloom, chromatic aberration, grain.

## 3.5.0

- Colour purpose modes: Assistant, Combat, Study, Creator, Business, Chill, Diagnostics, Stealth.

## 3.4.0

- Diagnostics scan, boot greeting, holographic notification cards.
