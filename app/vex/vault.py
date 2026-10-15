"""Local secret store: API keys and OAuth tokens encrypted with Windows DPAPI (only the user's Windows account can decrypt)."""
import os, json, base64, ctypes, threading, logging
from ctypes import wintypes
from . import config

log = logging.getLogger("vex.vault")
PATH = os.path.join(config.APP_DIR, "data", "vault.dpapi")
_lock = threading.Lock()
_cache = None


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _crypt(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        return data  # dev box only
    c = ctypes.windll.crypt32
    buf = ctypes.create_string_buffer(data, len(data))
    inp, out = _BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), _BLOB()
    ent = b"VexAssistant.vault.v1"; eb = ctypes.create_string_buffer(ent, len(ent))
    entb = _BLOB(len(ent), ctypes.cast(eb, ctypes.POINTER(ctypes.c_char)))
    fn = c.CryptProtectData if protect else c.CryptUnprotectData
    ok = fn(ctypes.byref(inp), "Vex" if protect else None, ctypes.byref(entb), None, None, 0x01, ctypes.byref(out)) if protect else \
         fn(ctypes.byref(inp), None, ctypes.byref(entb), None, None, 0x01, ctypes.byref(out))
    if not ok:
        raise OSError("DPAPI failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _load():
    global _cache
    if _cache is None:
        _cache = {}
        try:
            with open(PATH, "rb") as f:
                _cache = json.loads(_crypt(f.read(), False).decode())
        except FileNotFoundError:
            pass
        except Exception:
            log.exception("vault unreadable")
    return _cache


def _write():
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "wb") as f:
        f.write(_crypt(json.dumps(_cache).encode(), True))
    os.replace(tmp, PATH)


def get(name, default=""):
    with _lock:
        return _load().get(name, default)


def put(name, value):
    with _lock:
        d = _load()
        if value in (None, ""):
            d.pop(name, None)
        else:
            d[name] = value
        _write()


def has(name):
    return bool(get(name))


def selftest():
    return _crypt(_crypt(b"ok", True), False) == b"ok"
