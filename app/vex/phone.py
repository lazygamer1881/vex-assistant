"""Phone bridge: a tiny HTTP API on the home Wi-Fi so the user's iPhone can talk to Vex.

Safety:
  * listens ONLY on 127.0.0.1 and this PC's private LAN address (10.x / 172.16-31.x / 192.168.x), never 0.0.0.0
  * only answers clients that are themselves on a private LAN address or localhost
  * every API call needs the pairing key (header X-Vex-Key), compared in constant time
  * rate limited per device; 10 wrong keys in 10 min locks that device out for 10 min
  * commands go through the exact same Brain as voice: same "yes to confirm" rules (confirm with
    POST /confirm + the pending id) and the same never-rules (no buying, no signing in, no going live)

Endpoints (JSON in / JSON out):
  GET  /               phone web app (no key needed to load the page; it can't do anything without the key)
  GET  /ping           {ok, name}
  POST /command        {"text": "..."} -> {"reply", "needs_confirm", "confirm_id"}
  POST /confirm        {"id": "...", "yes": true|false} -> {"reply"}
"""
import os, re, json, time, socket, secrets, hmac, logging, threading, ipaddress, datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from . import config, actlog, tools

log = logging.getLogger("vex.phone")
PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "phone.html")
KEY_HEADER = "X-Vex-Key"
PRIVATE_NETS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o/1/l/i: easy to read and type
CONFIRM_SECONDS = 60
MAX_BODY = 4096


def new_key():
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(5)) for _ in range(4))  # ~98 bits


def ensure_key():
    k = config.get("phone_key")
    if not k or len(k) < 16:
        k = new_key()
        config.save({"phone_key": k})
    return k


def is_private(ip):
    try:
        a = ipaddress.ip_address(ip)
        if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
            a = a.ipv4_mapped
        return any(a in n for n in PRIVATE_NETS)
    except ValueError:
        return False


def is_local_client(ip):
    try:
        a = ipaddress.ip_address(ip)
        if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
            a = a.ipv4_mapped
        return a.is_loopback or is_private(str(a))
    except ValueError:
        return False


def lan_ips():
    """This PC's private IPv4 addresses (Wi-Fi / Ethernet), best one (has a default route) first."""
    ips = []
    try:  # the address Windows would use to reach the internet = the real LAN adapter
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))  # UDP connect sends nothing
        ips.append(s.getsockname()[0]); s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.append(info[4][0])
    except Exception:
        pass
    out = []
    for ip in ips:
        if is_private(ip) and ip not in out:
            out.append(ip)
    return out


def _speakable(text):
    """Voice replies say 'say yes'; on the phone you tap Yes."""
    text = re.sub(r"\b[Ss]ay yes\b", "Tap Yes", text or "")
    return re.sub(r"\bsay (?:send|send it)\b", "say send", text)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False  # never share the port with another program

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class PhoneBridge:
    def __init__(self, vex):
        self.vex = vex
        self.servers = {}      # ip -> server
        self.error = ""
        self.port = None
        self._hits = {}        # ip -> [timestamps]
        self._bad = {}         # ip -> [timestamps of wrong keys]
        self._locked = {}      # ip -> unlock time
        self._rl = threading.Lock()
        self._wake = threading.Event()

    # ------------------------------------------------------------ lifecycle
    def start(self):
        ensure_key()
        threading.Thread(target=self._loop, daemon=True, name="phone-bridge").start()

    def refresh(self):
        self._wake.set()

    def _loop(self):
        while True:
            try:
                self._sync()
            except Exception:
                log.exception("phone bridge sync")
            self._wake.wait(30)  # re-check every 30 s so a new Wi-Fi address (DHCP) is picked up
            self._wake.clear()

    def _sync(self):
        want = []
        port = int(config.get("phone_port") or 8765)
        if config.get("phone_enabled"):
            want = ["127.0.0.1"] + lan_ips()
        if port != self.port:
            self._stop_all()
            self.port = port
        for ip in list(self.servers):
            if ip not in want:
                self._stop(ip)
        errs = []
        for ip in want:
            if ip in self.servers:
                continue
            try:
                srv = _Server((ip, port), self._handler_class())
                threading.Thread(target=srv.serve_forever, daemon=True, name=f"phone-{ip}").start()
                self.servers[ip] = srv
                log.info("phone bridge listening on %s:%s", ip, port)
            except OSError as e:
                errs.append(f"{ip}:{port} ({e.strerror or e})")
                log.warning("phone bridge can't listen on %s:%s: %s", ip, port, e)
        self.error = ("Couldn't open " + ", ".join(errs)) if errs else ""

    def _stop(self, ip):
        srv = self.servers.pop(ip, None)
        if srv:
            try: srv.shutdown(); srv.server_close()
            except Exception: pass
            log.info("phone bridge stopped on %s", ip)

    def _stop_all(self):
        for ip in list(self.servers):
            self._stop(ip)

    def info(self):
        ips = [ip for ip in self.servers if ip != "127.0.0.1"]
        lan = ips[0] if ips else (lan_ips() or [""])[0]
        port = self.port or int(config.get("phone_port") or 8765)
        base = f"http://{lan}:{port}" if lan else ""
        return {"enabled": bool(config.get("phone_enabled")), "running": bool(ips), "ip": lan, "port": port,
                "base_url": base, "command_url": base + "/command" if base else "", "confirm_url": base + "/confirm" if base else "",
                "pair_url": f"{base}/#k={config.get('phone_key')}" if base else "", "key": config.get("phone_key"),
                "header": KEY_HEADER, "error": self.error, "hostname": socket.gethostname()}

    # ------------------------------------------------------------ guards
    def _rate_ok(self, ip):
        now = time.time()
        with self._rl:
            if self._locked.get(ip, 0) > now:
                return False
            h = [t for t in self._hits.get(ip, []) if now - t < 60] + [now]
            self._hits[ip] = h
            return len(h) <= 30  # 30 requests a minute per device

    def _bad_key(self, ip):
        now = time.time()
        with self._rl:
            b = [t for t in self._bad.get(ip, []) if now - t < 600] + [now]
            self._bad[ip] = b
            if len(b) >= 10:
                self._locked[ip] = now + 600
                self._bad[ip] = []
                actlog.write("BLOCKED", "phone bridge", {"ip": ip}, "10 wrong keys, locked out for 10 minutes")

    def _key_ok(self, given):
        k = config.get("phone_key") or ""
        return bool(k) and hmac.compare_digest((given or "").encode(), k.encode())

    # ------------------------------------------------------------ commands
    def _finish(self, res):
        """Shared post-processing of a Brain/tool result -> API reply dict."""
        v, b = self.vex, self.vex.brain
        if isinstance(res, str):
            res = {"say": res}
        res = res or {}
        if res.get("kill"):
            v.cancel_all("phone")
            actlog.CANCEL.clear()
        out = {"reply": _speakable(res.get("say", "")) or "Done.", "needs_confirm": False, "confirm_id": ""}
        if res.get("detail"):
            out["detail"] = res["detail"]
        p = b.pending_confirm
        if res.get("confirm") and p:
            p["id"] = secrets.token_hex(4)
            p["src"] = "phone"
            out.update(needs_confirm=True, confirm_id=p["id"], confirm_what=p.get("desc", ""))
            if "tap yes" not in out["reply"].lower():
                out["reply"] += " Tap Yes to confirm."
        if tools.has_pending_discord():
            out["discord_waiting"] = True
        v.emit("transcript", {"who": "vex", "text": out["reply"]})
        after = res.get("after")
        if after:
            def go():
                time.sleep(0.6)
                try: after()
                except Exception: log.exception("phone after")
            threading.Thread(target=go, daemon=True).start()
        return out

    def command(self, text):
        v, b = self.vex, self.vex.brain
        if not v._busy.acquire(timeout=45):
            return 503, {"reply": "I'm busy with something else, try again in a sec.", "needs_confirm": False, "confirm_id": ""}
        try:
            v.emit("transcript", {"who": "you", "text": "📱 " + text})
            from .brain import norm, CONFIRM_YES
            p = b.pending_confirm
            if p and time.time() - p["at"] < CONFIRM_SECONDS and norm(text).strip(" ,.!") in CONFIRM_YES:
                # on the phone a yes has to be the Yes button (POST /confirm with the id), not a typed/dictated "yes"
                p.setdefault("id", secrets.token_hex(4))
                return 200, {"reply": "Tap Yes to confirm " + (p.get("desc") or "that") + ".", "needs_confirm": True,
                             "confirm_id": p["id"], "confirm_what": p.get("desc", "")}
            actlog.CANCEL.clear()
            actlog.write("PHONE", "command", None, text[:200])
            try:
                res = b.handle(text)
            except Exception:
                log.exception("phone brain")
                res = {"say": "Apologies, something went wrong on my end."}
            if actlog.CANCEL.is_set() and not res.get("kill"):
                actlog.CANCEL.clear()
                return 200, {"reply": "Stopped.", "needs_confirm": False, "confirm_id": ""}
            return 200, self._finish(res)
        finally:
            v.set_state("sleeping" if v.listener.enabled else "paused")
            v._busy.release()

    def confirm(self, pid, yes):
        v, b = self.vex, self.vex.brain
        if not v._busy.acquire(timeout=45):
            return 503, {"reply": "I'm busy with something else, try again in a sec.", "needs_confirm": False, "confirm_id": ""}
        try:
            p = b.pending_confirm
            if not p or not pid or not hmac.compare_digest(str(p.get("id", "")), str(pid)):
                return 409, {"reply": "There's nothing waiting for a yes anymore.", "needs_confirm": False, "confirm_id": ""}
            b.pending_confirm = None
            if time.time() - p["at"] >= CONFIRM_SECONDS:
                actlog.write("DECLINED", p["desc"], None, "phone yes came too late (over 60 s)")
                return 410, {"reply": "That took too long so I didn't do it. Ask me again.", "needs_confirm": False, "confirm_id": ""}
            if yes is not True:
                actlog.write("DECLINED", p["desc"], None, "the user tapped No on phone")
                v.emit("transcript", {"who": "vex", "text": "Okay, I didn't do it."})
                return 200, {"reply": "Okay, I didn't do it.", "needs_confirm": False, "confirm_id": ""}
            actlog.write("CONFIRMED", p["desc"], None, "the user tapped Yes on phone")
            v.emit("transcript", {"who": "you", "text": "📱 Yes"})
            actlog.CANCEL.clear()
            try:
                res = p["fn"]()
            except Exception:
                log.exception("phone confirm")
                res = {"say": "Apologies, something went wrong on my end."}
            if isinstance(res, dict) and res.get("confirm"):  # a second risky step: wait for another yes
                b.pending_confirm = {"fn": res["confirm"], "desc": res.get("confirm_desc", ""), "at": time.time()}
            return 200, self._finish(res)
        finally:
            v.set_state("sleeping" if v.listener.enabled else "paused")
            v._busy.release()

    def chat(self, text, chat_id):
        from . import chat
        actlog.write("PHONE", "chat", None, text[:200])
        try:
            return 200, chat.chat_turn(self.vex, chat_id or None, text, source="phone")
        except Exception:
            log.exception("phone chat")
            return 200, {"reply": "Apologies, something went wrong on my end.", "needs_confirm": False}

    def chat_confirm(self, pid, yes):
        from . import chat
        p = self.vex.engine.pending
        if not p or not pid or not hmac.compare_digest(str(p.get("id", "")), pid):
            return 409, {"reply": "There's nothing waiting for a yes anymore.", "needs_confirm": False}
        actlog.write("CONFIRMED" if yes else "DECLINED", p.get("desc", ""), None, "phone button")
        return 200, chat.chat_confirm(self.vex, pid, yes)

    # ------------------------------------------------------------ HTTP
    def _handler_class(self):
        bridge = self

        class H(BaseHTTPRequestHandler):
            server_version = "Vex"
            sys_version = ""
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *a):
                log.info("%s %s", self.client_address[0], fmt % a)

            def _send(self, code, obj=None, body=None, ctype="application/json; charset=utf-8"):
                data = body if body is not None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(data)

            def _guard(self, need_key=True):
                ip = self.client_address[0]
                if not is_local_client(ip):
                    self._send(403, {"reply": "Only devices on your home Wi-Fi can use Vex."}); return False
                if not bridge._rate_ok(ip):
                    self._send(429, {"reply": "Slow down a sec, too many requests."}); return False
                if need_key and not bridge._key_ok(self.headers.get(KEY_HEADER)):
                    bridge._bad_key(ip)
                    self._send(401, {"reply": "Wrong or missing Vex key. Check the key in Vex Settings, Phone."}); return False
                return True

            def _json(self):
                n = int(self.headers.get("Content-Length") or 0)
                if n <= 0 or n > MAX_BODY:
                    return None
                try:
                    d = json.loads(self.rfile.read(n).decode("utf-8"))
                    return d if isinstance(d, dict) else None
                except Exception:
                    return None

            def do_GET(self):
                path = self.path.split("?")[0]
                if path in ("/", "/index.html"):
                    if not self._guard(need_key=False): return
                    try:
                        page = open(PAGE, "rb").read()
                    except Exception:
                        page = b"Vex phone page missing"
                    self._send(200, body=page, ctype="text/html; charset=utf-8")
                elif path == "/ping":
                    if not self._guard(): return
                    self._send(200, {"ok": True, "name": config.get("assistant_name"), "reply": "Vex is connected."})
                else:
                    self._send(404, {"reply": "Not found."})

            def do_POST(self):
                path = self.path.split("?")[0]
                if path not in ("/command", "/confirm", "/chat", "/chat_confirm"):
                    self._send(404, {"reply": "Not found."}); return
                if not self._guard(): return
                d = self._json()
                if d is None:
                    self._send(400, {"reply": "Send JSON like {\"text\": \"what time is it\"}."}); return
                if path == "/chat":
                    text = str(d.get("text") or "").strip()[:8000]
                    if not text:
                        self._send(400, {"reply": "I didn't catch anything."}); return
                    code, out = bridge.chat(text, str(d.get("chat_id") or "")[:40])
                elif path == "/chat_confirm":
                    yes = d.get("yes")
                    code, out = bridge.chat_confirm(str(d.get("id") or ""), yes is True or (isinstance(yes, str) and yes.lower() in ("true", "yes", "1")))
                elif path == "/command":
                    text = str(d.get("text") or "").strip()[:500]
                    if not text:
                        self._send(400, {"reply": "I didn't catch anything.", "needs_confirm": False, "confirm_id": ""}); return
                    code, out = bridge.command(text)
                else:
                    yes = d.get("yes")
                    if isinstance(yes, str):
                        yes = yes.strip().lower() in ("true", "yes", "1")
                    code, out = bridge.confirm(str(d.get("id") or ""), yes is True)
                self._send(code, out)

            def do_OPTIONS(self):  # no CORS: other websites can't call Vex from a browser
                self._send(405, {"reply": "Not allowed."})

        return H
