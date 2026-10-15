"""Vex 2.3: proactive awareness, status reports, screen reading, routines, HUD feed. Original code."""
import os, re, time, json, shutil, datetime, logging, threading, subprocess, collections, tempfile
from . import config, assist, actlog

log = logging.getLogger("vex.ops")
FEED = collections.deque(maxlen=40)          # HUD notification feed
_last = {}                                    # alert kind -> last time
core = None                                   # set by core.Vex.start()


def feed(kind, text):
    FEED.appendleft({"t": datetime.datetime.now().strftime("%I:%M %p").lstrip("0"), "kind": kind, "text": text})
    if core:
        try: core.emit("feed", FEED[0])
        except Exception: pass


def _quiet():
    h = datetime.datetime.now().hour
    if config.get("focus_until") and time.time() < float(config.get("focus_until") or 0):
        return True
    return h >= int(config.get("quiet_start") or 23) or h < int(config.get("quiet_end") or 7)


def alert(kind, text, offer=None, every_min=30):
    """Rate-limited proactive line. Spoken only in conversation mode (and not in quiet hours); otherwise a toast."""
    now = time.time()
    if now - _last.get(kind, 0) < every_min * 60:
        return
    _last[kind] = now
    feed("alert", text)
    actlog.write("INFO", "proactive", {"kind": kind}, text)
    if not core:
        return
    if offer:
        core.brain.pending_yes = offer          # "yes" right after = do it
    if core.state in ("listening",) and not _quiet() and config.get("proactive_voice", True):
        threading.Thread(target=lambda: core.say(text), daemon=True).start()
    else:
        core.emit("notify", {"title": "Vex", "text": text})
        if core.tray_notify:
            try: core.tray_notify("Vex", text)
            except Exception: pass


def monitor_loop():
    hot = collections.deque(maxlen=6)
    while True:
        time.sleep(30)
        if not config.get("proactive_alerts", True):
            continue
        try:
            s = assist.pc_stats()
            hot.append(s.get("cpu") or 0)
            if len(hot) == hot.maxlen and min(hot) >= 90:
                alert("cpu", f"CPU has been above 90 percent for three minutes, sir.")
            if (s.get("gpu_temp") or 0) >= 84:
                alert("gputemp", f"The graphics card is running hot at {s['gpu_temp']} degrees.")
            if s.get("disk_free") is not None and s["disk_free"] < int(config.get("low_disk_gb") or 15):
                from . import pc
                alert("disk", f"Drive C is down to {s['disk_free']} gigabytes free. Shall I clear the caches?", offer=pc._clean_disk_now, every_min=240)
            if (s.get("ram") or 0) >= 93:
                alert("ram", f"Memory is at {s['ram']} percent. Something's being greedy.")
            soon = [r for r in assist.reminders() if not r["done"] and 0 < (datetime.datetime.fromisoformat(r["due"]) - datetime.datetime.now()).total_seconds() <= 600]
            for r in soon:
                alert("rem:" + r["text"], f"Heads up: {r['text']} in about ten minutes.", every_min=60 * 24)
        except Exception:
            log.exception("monitor")


def status_report():
    s = assist.pc_stats()
    parts = [f"All systems nominal, sir." if (s.get("cpu") or 0) < 85 and (s.get("disk_free") or 99) >= 15 else "Mostly fine, sir, with a caveat or two."]
    parts.append(f"CPU at {s.get('cpu') if s.get('cpu') is not None else 'unknown'} percent, memory {s.get('ram') if s.get('ram') is not None else 'unknown'} percent" + (f", GPU {s['gpu']} percent at {s['gpu_temp']} degrees" if s.get("gpu") is not None else "") + ".")
    if s.get("disk_free") is not None:
        parts.append(f"Drive C has {s['disk_free']} gigabytes free" + (", which is getting tight." if s["disk_free"] < 40 else "."))
    try:
        w = assist.weather_data(config.get("weather_city") or ""); parts.append(f"Outside it's {w['temp']} degrees and {w['desc']}.")
    except Exception:
        pass
    r = [x for x in assist.reminders() if not x["done"] and x["due"][:10] == datetime.date.today().isoformat()]
    t = [x for x in assist.todos() if not x.get("done")]
    parts.append((f"{len(r)} reminder{'s' if len(r) != 1 else ''} today" if r else "No reminders today") + (f" and {len(t)} task{'s' if len(t) != 1 else ''} open." if t else "."))
    out = " ".join(parts); feed("status", out); return out


def read_screen():
    """Screenshot of the main screen + Windows' built-in OCR (no downloads). Returns text."""
    ps = r'''
Add-Type -AssemblyName System.Windows.Forms,System.Drawing,System.Runtime.WindowsRuntime
$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height
$g=[System.Drawing.Graphics]::FromImage($bmp);$g.CopyFromScreen($b.X,$b.Y,0,0,$b.Size);$p="$env:TEMP\vex_screen.png";$bmp.Save($p);$g.Dispose();$bmp.Dispose()
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime];$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics,ContentType=WindowsRuntime]
$aw=([System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0]
function W($op,$t){$x=$aw.MakeGenericMethod($t).Invoke($null,@($op));$x.Wait(-1)|Out-Null;$x.Result}
$f=W ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile])
$s=W ($f.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$d=W ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s)) ([Windows.Graphics.Imaging.BitmapDecoder])
$sb=W ($d.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$e=[Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages();$r=W ($e.RecognizeAsync($sb)) ([Windows.Media.Ocr.OcrResult])
$s.Dispose();Remove-Item $p -ErrorAction SilentlyContinue;$r.Lines|%{$_.Text}
'''
    fd, path = tempfile.mkstemp(suffix=".ps1"); os.close(fd)
    open(path, "w", encoding="utf-8").write(ps)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path], capture_output=True, text=True, timeout=40, creationflags=0x08000000)
        return r.stdout.strip()
    finally:
        os.remove(path)


def describe_screen(ask_llm):
    try:
        txt = read_screen()
    except Exception as e:
        return f"I couldn't read the screen ({e})."
    if not txt:
        return "I can't make out any text on the main screen, sir."
    try:
        return ask_llm("In two short spoken sentences, say what the user is looking at, based on this text read from their screen:\n" + txt[:2500])
    except Exception:
        return "I can see text starting with: " + " ".join(txt.split()[:25])


# ------------------------------------------------------------ routines
def gaming_mode():
    from . import tools, pc
    from .actlog import ask
    import ctypes
    open_line = tools.open_apps(["steam", "discord", "obs"])
    feed("routine", "Gaming mode: Steam, Discord, OBS (no stream started)")
    names = [n for n in ("chrome.exe", "opera.exe") if n.lower() in subprocess.run(["tasklist"], capture_output=True, text=True, creationflags=0x08000000).stdout.lower()]
    if not names:
        return open_line + " Gaming mode engaged. I haven't started any stream or recording."
    return ask(open_line + f" {', '.join(n[:-4].title() for n in names)} is still open in the background. Shall I close it? Any unsaved tabs might be lost.",
               "gaming mode: close " + ", ".join(names),
               lambda: (subprocess.run(["taskkill", "/IM", names[0]] + (["/IM", names[1]] if len(names) > 1 else []), capture_output=True, creationflags=0x08000000), "Closed. Gaming mode engaged.")[1])


def goodnight():
    t = datetime.date.today() + datetime.timedelta(days=1)
    r = [x for x in assist.reminders() if not x["done"] and x["due"][:10] == t.isoformat()]
    td = [x for x in assist.todos() if not x.get("done")]
    msg = "Goodnight, sir. " + (f"Tomorrow you've {len(r)} reminder{'s' if len(r) != 1 else ''}, first: {r[0]['text']}. " if r else "Nothing scheduled for tomorrow. ") + \
          (f"{len(td)} task{'s' if len(td) != 1 else ''} still open. " if td else "") + "I'll dim the monitors."
    feed("routine", "Goodnight")

    def after():
        time.sleep(1.5)
        try:
            import ctypes
            ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)  # monitors off (any mouse move wakes them)
        except Exception:
            pass
    return {"say": msg, "after": after, "sleep": True}
