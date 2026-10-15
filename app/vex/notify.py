"""Push notifications to the user's OWN phone via ntfy.sh (free, no account). Only ever posts to his private topic."""
import secrets, urllib.request, logging
from . import config

log = logging.getLogger("vex.notify")


def topic():
    return (config.get("ntfy_topic") or "").strip()


def push(message, title="Vex"):
    message = (message or "").strip()[:800] or "Ping from Vex."
    if not topic():
        return "Phone notifications are off. Add your own private ntfy topic in Settings > Phone first."
    req = urllib.request.Request(f"https://ntfy.sh/{topic()}", data=message.encode("utf-8"), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode() or "Vex", "Tags": "robot"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            ok = r.status == 200
    except Exception as e:
        log.warning("ntfy: %s", e)
        return "I couldn't reach the notification service just now, sir."
    return "Sent to your phone." if ok else "The notification service didn't accept it."
