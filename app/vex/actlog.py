"""Action log + shared kill switch.

Every action Vex takes (or is asked to take) is written to <install>/actions.log:
  time | STATUS | action | args | result
STATUS: DONE, DRY-RUN, ASKED (waiting for "yes"), CONFIRMED, DECLINED, BLOCKED, CANCELLED, ERROR
"""
import os, json, time, threading, functools, datetime
from . import config

LOG_PATH = os.path.join(config.APP_DIR, "actions.log")
CANCEL = threading.Event()   # set by "Vex stop" -> every running/queued action bails out
_lock = threading.Lock()


def write(status, action, args=None, result=""):
    try:
        a = json.dumps(args, default=str, ensure_ascii=False) if args else ""
    except Exception:
        a = str(args)
    r = result.get("say", "") if isinstance(result, dict) else str(result or "")
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {status:<9} | {action} | {a[:300]} | {r[:300].replace(chr(10), ' ')}\n"
    with _lock:
        try:
            if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 5_000_000:
                os.replace(LOG_PATH, LOG_PATH + ".old")
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def logged(fn):
    """Decorator: logs every call of an action and honours the kill switch."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        from . import tools
        call_args = {"args": list(args), **kwargs} if args else kwargs
        if CANCEL.is_set():
            write("CANCELLED", fn.__name__, call_args, "skipped after Vex stop")
            return "Stopped."
        try:
            r = fn(*args, **kwargs)
        except Exception as e:
            write("ERROR", fn.__name__, call_args, f"{type(e).__name__}: {e}")
            raise
        if isinstance(r, dict) and r.get("confirm"):
            status = "ASKED"
        elif isinstance(r, dict) and r.get("blocked"):
            status = "BLOCKED"
        elif tools.DRY_RUN:
            status = "DRY-RUN"
        else:
            status = "DONE"
        write(status, fn.__name__, call_args, r)
        return r
    return wrapper


def ask(say, action_desc, fn):
    """A reply that needs the user to say "yes" before fn runs."""
    return {"say": say, "confirm": fn, "confirm_desc": action_desc}


def blocked(say):
    return {"say": say, "blocked": True}
