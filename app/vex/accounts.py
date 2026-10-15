"""Vex 3.2 account connections (opt-in). the user completes each OAuth sign-in himself in his own browser;
Vex never sees his password. Tokens are stored encrypted (DPAPI vault). Disconnect deletes them."""
import os, json, time, base64, hashlib, secrets, threading, logging, urllib.parse, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from . import config, vault

log = logging.getLogger("vex.accounts")
REDIRECT_PORT = 8766
REDIRECT = f"http://127.0.0.1:{REDIRECT_PORT}/callback"
PROVIDERS = {
    "spotify": {"label": "Spotify", "auth": "https://accounts.spotify.com/authorize", "token": "https://accounts.spotify.com/api/token",
                "scopes": ["user-read-currently-playing", "user-read-playback-state"],
                "explain": ["See what song is playing", "See your playback device"], "setup": "Create a free app at developer.spotify.com/dashboard, add redirect URI " + REDIRECT + ", paste its Client ID."},
    "google": {"label": "Google (Calendar + Gmail, read-only)", "auth": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
               "scopes": ["https://www.googleapis.com/auth/calendar.readonly", "https://www.googleapis.com/auth/gmail.readonly"],
               "explain": ["Read your calendar events", "Read your Gmail (count unread, read subjects). Cannot send or delete."],
               "setup": "In Google Cloud Console create an OAuth client of type 'Desktop app', paste its Client ID and Client secret.", "extra": {"access_type": "offline", "prompt": "consent"}},
    "youtube": {"label": "YouTube (channel stats, read-only)", "auth": "https://accounts.google.com/o/oauth2/v2/auth", "token": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/youtube.readonly"], "explain": ["Read your channel's subscriber, view and video counts"],
                "setup": "Same Google 'Desktop app' OAuth client works; enable the YouTube Data API v3.", "extra": {"access_type": "offline", "prompt": "consent"}},
}
_flow = {}


def _acc():
    return dict(config.get("accounts") or {})


def listing():
    a = _acc(); out = []
    for n, p in PROVIDERS.items():
        tok = vault.get("oauth_" + n)
        out.append({"id": n, "label": p["label"], "scopes": p["explain"], "setup": p["setup"], "redirect": REDIRECT,
                    "client_id": (a.get(n) or {}).get("client_id", ""), "connected": bool(tok), "pending": _flow.get("name") == n,
                    "since": (a.get(n) or {}).get("since", "")})
    out.append({"id": "discord", "label": "Discord webhook (post to one channel)", "scopes": ["Post messages to the one channel the webhook belongs to. Always asks 'Shall I proceed?' first."],
                "setup": "In Discord: Channel settings > Integrations > Webhooks > New webhook > Copy URL, paste it here.", "connected": bool(config.get("discord_webhook_url")), "webhook": True})
    return out


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def connect(name, client_id, client_secret=""):
    """Starts the OAuth flow. Opens the provider's own sign-in page in the user's default browser (he signs in there)."""
    if name not in PROVIDERS: return {"ok": False, "msg": "Unknown account"}
    client_id = (client_id or "").strip()
    if not client_id: return {"ok": False, "msg": "Paste your Client ID first. " + PROVIDERS[name]["setup"]}
    a = _acc(); a[name] = {"client_id": client_id, "since": (a.get(name) or {}).get("since", "")}; config.save({"accounts": a})
    if client_secret: vault.put("oauth_secret_" + name, client_secret.strip())
    p = PROVIDERS[name]; ver = _b64(secrets.token_bytes(48)); state = secrets.token_urlsafe(16)
    q = {"client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT, "scope": " ".join(p["scopes"]), "state": state,
         "code_challenge": _b64(hashlib.sha256(ver.encode()).digest()), "code_challenge_method": "S256", **p.get("extra", {})}
    _flow.clear(); _flow.update(name=name, verifier=ver, state=state, client_id=client_id, at=time.time())
    threading.Thread(target=_serve_once, daemon=True).start()
    url = p["auth"] + "?" + urllib.parse.urlencode(q)
    try:
        os.startfile(url)  # the user's default browser; he completes sign-in + consent himself
    except Exception:
        return {"ok": True, "msg": "Open this link to finish: " + url, "url": url}
    log.info("oauth: started %s flow (waiting for the user to approve in his browser)", name)
    return {"ok": True, "msg": "Finish sign-in in your browser. Vex is waiting (5 min)."}


def _serve_once():
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
            ok, msg = False, "Unexpected request."
            if u.path == "/callback" and q.get("state") == _flow.get("state"):
                if q.get("code"):
                    try: _exchange(q["code"]); ok, msg = True, "Connected. You can close this tab and go back to Vex."
                    except Exception as e: msg = "Couldn't finish: " + str(e)[:200]
                else:
                    msg = "Cancelled: " + q.get("error", "no code")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(f"<body style='background:#01030a;color:#7fefff;font:16px monospace;padding:40px'>VEX // {msg}</body>".encode())
            H.done = True
    H.done = False
    try:
        srv = HTTPServer(("127.0.0.1", REDIRECT_PORT), H); srv.timeout = 5
    except OSError as e:
        log.warning("oauth: callback port busy: %s", e); return
    end = time.time() + 300
    while not H.done and time.time() < end:
        srv.handle_request()
    srv.server_close(); _flow.clear()


def _exchange(code):
    name = _flow["name"]; p = PROVIDERS[name]
    body = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "client_id": _flow["client_id"], "code_verifier": _flow["verifier"]}
    sec = vault.get("oauth_secret_" + name)
    if sec: body["client_secret"] = sec
    tok = _post_form(p["token"], body)
    tok["obtained"] = time.time(); vault.put("oauth_" + name, json.dumps(tok))
    a = _acc(); a.setdefault(name, {})["since"] = time.strftime("%Y-%m-%d %H:%M"); config.save({"accounts": a})
    log.info("oauth: %s connected", name)


def _post_form(url, body):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(body).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:200].decode('utf8', 'replace')}")


def disconnect(name):
    if name == "discord":
        config.save({"discord_webhook_url": ""}); return {"ok": True, "msg": "Discord webhook removed."}
    vault.put("oauth_" + name, ""); vault.put("oauth_secret_" + name, "")
    a = _acc(); a.pop(name, None); config.save({"accounts": a})
    log.info("oauth: %s disconnected", name)
    return {"ok": True, "msg": PROVIDERS.get(name, {}).get("label", name) + " disconnected and token deleted."}


def set_discord(url):
    url = (url or "").strip()
    if url and not url.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        return {"ok": False, "msg": "That doesn't look like a Discord webhook URL."}
    config.save({"discord_webhook_url": url}); return {"ok": True, "msg": "Saved (encrypted)." if url else "Removed."}


def _token(name):
    raw = vault.get("oauth_" + name)
    if not raw: return None
    t = json.loads(raw)
    if time.time() > t.get("obtained", 0) + int(t.get("expires_in", 3600)) - 60 and t.get("refresh_token"):
        body = {"grant_type": "refresh_token", "refresh_token": t["refresh_token"], "client_id": (_acc().get(name) or {}).get("client_id", "")}
        sec = vault.get("oauth_secret_" + name)
        if sec: body["client_secret"] = sec
        n = _post_form(PROVIDERS[name]["token"], body); n.setdefault("refresh_token", t["refresh_token"]); n["obtained"] = time.time()
        vault.put("oauth_" + name, json.dumps(n)); t = n
    return t["access_token"]


def _get(name, url):
    tok = _token(name)
    if not tok: raise RuntimeError(f"{PROVIDERS[name]['label']} isn't connected. Connect it in the Connections tab.")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = r.read().decode(); return json.loads(d) if d else {}


# ---------------- read-only skills
def spotify_now():
    d = _get("spotify", "https://api.spotify.com/v1/me/player/currently-playing")
    if not d or not d.get("item"): return "Nothing's playing on Spotify."
    return f"{d['item']['name']} by {', '.join(a['name'] for a in d['item']['artists'])}."


def calendar_next():
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = _get("google", "https://www.googleapis.com/calendar/v3/calendars/primary/events?" + urllib.parse.urlencode({"timeMin": now, "maxResults": 3, "singleEvents": "true", "orderBy": "startTime"}))
    ev = d.get("items") or []
    if not ev: return "Your calendar is clear."
    return "Next up: " + "; ".join(f"{e.get('summary', 'event')} at {(e['start'].get('dateTime') or e['start'].get('date'))[:16].replace('T', ' ')}" for e in ev) + "."


def gmail_unread():
    d = _get("google", "https://gmail.googleapis.com/gmail/v1/users/me/labels/INBOX")
    return f"You have {d.get('messagesUnread', 0)} unread emails."


def youtube_stats():
    d = _get("youtube", "https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet&mine=true")
    it = (d.get("items") or [{}])[0]; s = it.get("statistics", {})
    return f"{it.get('snippet', {}).get('title', 'Your channel')}: {int(s.get('subscriberCount', 0)):,} subscribers, {int(s.get('viewCount', 0)):,} views, {s.get('videoCount', 0)} videos."


def discord_post(text):
    u = config.get("discord_webhook_url")
    if not u: raise RuntimeError("No Discord webhook set.")
    req = urllib.request.Request(u, data=json.dumps({"content": text[:1900]}).encode(), headers={"Content-Type": "application/json", "User-Agent": "Vex"})
    urllib.request.urlopen(req, timeout=15).read()
    return "Posted to Discord."
