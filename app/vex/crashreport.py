"""4.3: local crash reports. Nothing is ever sent anywhere.

Uncaught errors (main thread and worker threads) are written to logs/crash-report.txt with personal paths
and the Windows user name blanked out, so the file is safe to share if you want help."""
import os, sys, re, time, platform, threading, traceback, logging

log = logging.getLogger("vex.crash")
_APP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(_APP, "logs")
PATH = os.path.join(LOG_DIR, "crash-report.txt")
MAX_BYTES = 400_000


def sanitize(text):
    """Blanks the user's home folder, Windows user name and computer name out of a report."""
    s = str(text or "")
    reps = []
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    for v, tag in ((home, "%USERPROFILE%"), (os.environ.get("COMPUTERNAME", ""), "<pc>"), (os.environ.get("USERNAME", ""), "<user>")):
        if v and len(v) >= 3:
            reps.append((v, tag))
    for v, tag in reps:
        for form in {v, v.replace("\\", "/")}:
            s = re.sub(r"(?<![A-Za-z0-9])" + re.escape(form) + r"(?![A-Za-z0-9])", lambda m, t=tag: t, s, flags=re.I)
    s = re.sub(r"(?i)([A-Z]:\\Users\\)[^\\/\s\"']+", r"\1<user>", s)
    s = re.sub(r"(?i)(key|token|secret|password|authorization)([\"'=: ]+)[^\s\"',}]{6,}", r"\1\2<hidden>", s)
    return s


def _header():
    try:
        from . import __version__ as v
    except Exception:
        v = "?"
    return (f"Vex {v} | Python {platform.python_version()} | {platform.system()} {platform.release()} ({platform.version()}) | "
            f"{platform.machine()}")


def write(title, exc_type=None, exc=None, tb=None, extra=""):
    """Appends one report (newest last) and trims the file so it never grows big."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        body = "".join(traceback.format_exception(exc_type, exc, tb)) if exc_type else ""
        rec = (f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} - {title}\n{_header()}\n{body}{extra}\n")
        old = ""
        if os.path.exists(PATH):
            with open(PATH, encoding="utf-8", errors="replace") as f:
                old = f.read()
        txt = (old + sanitize(rec))[-MAX_BYTES:]
        with open(PATH, "w", encoding="utf-8") as f:
            f.write(txt)
    except Exception:
        pass
    return PATH


def install():
    """Hooks uncaught exceptions in the main thread and in every worker thread."""
    prev = sys.excepthook

    def hook(t, e, tb):
        if not issubclass(t, KeyboardInterrupt):
            write("uncaught error", t, e, tb)
            try: log.error("uncaught error", exc_info=(t, e, tb))
            except Exception: pass
        try: prev(t, e, tb)
        except Exception: pass
    sys.excepthook = hook

    def thook(a):
        if a.exc_type is SystemExit:
            return
        write(f"error in thread {getattr(a.thread, 'name', '?')}", a.exc_type, a.exc_value, a.exc_traceback)
        try: log.error("thread error", exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
        except Exception: pass
    threading.excepthook = thook


def info():
    ok = os.path.exists(PATH)
    n = 0
    if ok:
        try:
            with open(PATH, encoding="utf-8", errors="replace") as f:
                n = f.read().count("===== ")
        except Exception:
            pass
    return {"path": PATH, "exists": ok, "reports": n, "size": os.path.getsize(PATH) if ok else 0}


def text():
    """The report plus the last 60 log lines, sanitised (what 'Copy crash report' puts on the clipboard)."""
    out = ""
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8", errors="replace") as f:
            out = f.read()[-60000:]
    lp = os.path.join(LOG_DIR, "vex.log")
    if os.path.exists(lp):
        try:
            with open(lp, encoding="utf-8", errors="replace") as f:
                tail = f.readlines()[-60:]
            out += "\n===== last log lines\n" + "".join(tail)
        except Exception:
            pass
    return sanitize(out or "No crash reports. Everything has been running fine.\n" + _header())
