"""4.3: optional update check against a public JSON file.

Off until an address is set (config "update_url"). The request is a plain GET of that one file:
no ID, no stats, nothing about you or your PC is sent. Expected JSON:
  {"version": "4.3.1", "url": "https://.../download", "notes": "what changed"}
Vex only tells you about a newer version; it never downloads or installs anything by itself."""
import json, re, urllib.request, logging
from . import config, __version__

log = logging.getLogger("vex.update")


def _v(s):
    return tuple(int(x) for x in re.findall(r"\d+", str(s))[:4]) or (0,)


def check(timeout=8):
    url = (config.get("update_url") or "").strip()
    if not url:
        return {"ok": False, "configured": False, "current": __version__, "msg": "Update checks are off (no update address set)."}
    if not url.lower().startswith("https://"):
        return {"ok": False, "configured": True, "current": __version__, "msg": "The update address must start with https://"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VexAssistant", "Cache-Control": "no-cache"})
        d = json.loads(urllib.request.urlopen(req, timeout=timeout).read(65536).decode("utf-8", "replace"))
        latest = str(d.get("version") or "")
        newer = _v(latest) > _v(__version__)
        link = str(d.get("url") or "")
        if link and not link.lower().startswith("https://"):
            link = ""
        return {"ok": True, "configured": True, "current": __version__, "latest": latest, "newer": newer, "url": link,
                "notes": str(d.get("notes") or "")[:600],
                "msg": f"Version {latest} is available." if newer else f"You're up to date ({__version__})."}
    except Exception as e:
        log.info("update check: %s", e)
        return {"ok": False, "configured": True, "current": __version__, "msg": f"Couldn't check for updates ({type(e).__name__})."}
