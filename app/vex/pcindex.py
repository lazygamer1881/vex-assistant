"""Vex 2.6: local index of the whole PC (apps, games, settings pages, Control Panel, user files) + search.

Built in a background thread on start and every few hours; it sleeps between chunks so it stays light.
Skips AppData, system folders, browser profiles and anything that looks like a secret.
Small docs (txt, md, docx, pdf, cs, py) get a keyword index of their text, plus embeddings from
nomic-embed-text through Ollama when that model is installed (falls back to keywords only).
"""
import os, re, json, time, math, glob, string, zipfile, threading, logging, datetime, urllib.request, collections

from . import config

log = logging.getLogger("vex.index")
UP = os.environ.get("USERPROFILE", os.path.expanduser("~"))
IDX_DIR = os.path.join(config.APP_DIR, "data", "index")
os.makedirs(IDX_DIR, exist_ok=True)
IDX_PATH = os.path.join(IDX_DIR, "index.json")
EMB_PATH = os.path.join(IDX_DIR, "embeddings.npy")
REFRESH_H = 4
MAX_FILES = 80000
DOC_EXT = {".txt", ".md", ".docx", ".pdf", ".cs", ".py"}
SKIP_DIRS = {"appdata", "node_modules", ".git", ".svn", "__pycache__", ".venv", "venv", "library", "temp", "tmp", "obj", "logs",
             "user data", "profiles", "cache", "caches", ".cache", "$recycle.bin", "system volume information", "windows",
             "program files", "program files (x86)", "programdata", ".vs", ".idea", "build", "builds", "vexassistant", ".ollama"}
SECRET = re.compile(r"(passw|passwd|credential|secret|token|private[_ -]?key|id_rsa|id_ed25519|\.pem$|\.pfx$|\.p12$|\.kdbx?$|\.key$|"
                    r"^\.env|wallet|recovery[_ -]?codes?|2fa|backup[_ -]?codes?|cookies?|login data)", re.I)

SETTINGS_PAGES = {
    "display": "ms-settings:display", "screen resolution": "ms-settings:display", "night light": "ms-settings:nightlight",
    "sound": "ms-settings:sound", "audio": "ms-settings:sound", "volume mixer": "ms-settings:apps-volume", "sound devices": "ms-settings:sound-devices",
    "bluetooth": "ms-settings:bluetooth", "devices": "ms-settings:bluetooth", "printers": "ms-settings:printers", "mouse": "ms-settings:mousetouchpad",
    "wifi": "ms-settings:network-wifi", "wi-fi": "ms-settings:network-wifi", "network": "ms-settings:network-status", "ethernet": "ms-settings:network-ethernet",
    "vpn": "ms-settings:network-vpn", "airplane mode": "ms-settings:network-airplanemode", "proxy": "ms-settings:network-proxy",
    "storage": "ms-settings:storagesense", "disk": "ms-settings:storagesense", "startup apps": "ms-settings:startupapps", "startup": "ms-settings:startupapps",
    "apps": "ms-settings:appsfeatures", "installed apps": "ms-settings:appsfeatures", "default apps": "ms-settings:defaultapps",
    "power": "ms-settings:powersleep", "power and sleep": "ms-settings:powersleep", "battery": "ms-settings:batterysaver",
    "windows update": "ms-settings:windowsupdate", "updates": "ms-settings:windowsupdate", "about": "ms-settings:about", "system": "ms-settings:about",
    "notifications": "ms-settings:notifications", "focus": "ms-settings:quiethours", "do not disturb": "ms-settings:quiethours",
    "personalization": "ms-settings:personalization", "background": "ms-settings:personalization-background", "colors": "ms-settings:colors",
    "themes": "ms-settings:themes", "lock screen": "ms-settings:lockscreen", "taskbar": "ms-settings:taskbar",
    "gaming": "ms-settings:gaming-gamebar", "game mode": "ms-settings:gaming-gamemode", "game bar": "ms-settings:gaming-gamebar",
    "graphics": "ms-settings:display-advancedgraphics", "multitasking": "ms-settings:multitasking", "clipboard": "ms-settings:clipboard",
    "microphone": "ms-settings:privacy-microphone", "camera": "ms-settings:privacy-webcam", "privacy": "ms-settings:privacy",
    "accounts": "ms-settings:yourinfo", "sign in options": "ms-settings:signinoptions", "date and time": "ms-settings:dateandtime",
    "time": "ms-settings:dateandtime", "language": "ms-settings:regionlanguage", "keyboard": "ms-settings:typing",
    "accessibility": "ms-settings:easeofaccess", "windows security": "windowsdefender:", "recovery": "ms-settings:recovery",
    "settings": "ms-settings:",
}
CONTROL_PANEL = {
    "control panel": "control", "programs and features": "appwiz.cpl", "uninstall a program": "appwiz.cpl",
    "sound control panel": "mmsys.cpl", "playback devices": "mmsys.cpl", "recording devices": "mmsys.cpl",
    "network connections": "ncpa.cpl", "power options": "powercfg.cpl", "mouse properties": "main.cpl", "system properties": "sysdm.cpl",
    "environment variables": "rundll32.exe sysdm.cpl,EditEnvironmentVariables", "device manager": "devmgmt.msc", "disk management": "diskmgmt.msc",
    "task manager": "taskmgr", "firewall": "firewall.cpl", "internet options": "inetcpl.cpl", "fonts": "control fonts",
    "services": "services.msc", "event viewer": "eventvwr.msc", "game controllers": "joy.cpl", "region": "intl.cpl",
}

STATE = {"data": None, "emb": None, "building": False, "built_at": 0}
_lock = threading.Lock()
TOK = re.compile(r"[a-z0-9]{2,}")


def toks(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "")
    return TOK.findall(s.lower().replace("_", " "))


# ------------------------------------------------------------------ roots
def roots():
    od = os.path.join(UP, "OneDrive")
    r = []
    for n in ("Desktop", "Documents", "Downloads", "Videos", "Pictures", "Music"):
        for base in (od, UP):
            p = os.path.join(base, n)
            if os.path.isdir(p) and p not in r:
                r.append(p)
    for extra in [od, ] + \
                 [f"{d}:\\My Drive" for d in "GHIJ"] + (config.get("index_extra_roots") or []):
        if os.path.isdir(extra) and extra not in r:
            r.append(extra)
    return r


def _doc_text(path, ext):
    try:
        if ext == ".docx":
            with zipfile.ZipFile(path) as z:
                x = z.read("word/document.xml").decode("utf8", "ignore")
            return re.sub(r"<[^>]+>", " ", x)[:6000]
        if ext == ".pdf":
            from pypdf import PdfReader
            rd = PdfReader(path)
            return " ".join((p.extract_text() or "") for p in rd.pages[:5])[:6000]
        with open(path, encoding="utf8", errors="ignore") as f:
            return f.read(6000)
    except Exception:
        return ""


def _walk_files():
    files, n = [], 0
    for root in roots():
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d.lower() not in SKIP_DIRS and not d.startswith(".") and not SECRET.search(d)]
            for fn in fns:
                if SECRET.search(fn) or fn.lower() in ("desktop.ini", "thumbs.db") or fn.startswith("~$"):
                    continue
                p = os.path.join(dp, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                ext = os.path.splitext(fn)[1].lower()
                item = {"name": fn, "path": p, "kind": "file", "size": st.st_size, "mtime": int(st.st_mtime)}
                if ext in DOC_EXT and st.st_size < 400_000:
                    item["text"] = re.sub(r"\s+", " ", _doc_text(p, ext))[:3000]
                files.append(item)
                n += 1
                if n % 500 == 0:
                    time.sleep(0.05)  # stay light
                if n >= MAX_FILES:
                    return files
            # folders too, so "find my Haunted Tree files" can hit the project folder
            for d in dns:
                files.append({"name": d, "path": os.path.join(dp, d), "kind": "folder", "mtime": 0})
    return files


def _apps():
    from . import pc, tools, resolve
    apps = [{"name": a["name"], "path": "shell:AppsFolder\\" + a["id"], "kind": "app"} for a in pc.start_apps()]
    seen = {a["name"].lower() for a in apps}
    for s in tools._shortcut_files():
        n = os.path.splitext(os.path.basename(s))[0]
        if n.lower() not in seen:
            seen.add(n.lower()); apps.append({"name": n, "path": s, "kind": "app"})
    resolve._games["items"] = None
    games = [{"name": g["name"], "path": g["uri"], "kind": "game", "src": g["src"]} for g in resolve.games()]
    for a in apps:   # Roblox / Minecraft / launchers count as games too
        if re.search(r"roblox|minecraft|fortnite|gorilla tag|ravenfield|rocket league|epic games", a["name"], re.I) and a["name"].lower() not in {g["name"].lower() for g in games}:
            games.append({"name": a["name"], "path": a["path"], "kind": "game", "src": "Start menu"})
    return apps, games


def build():
    if STATE["building"]:
        return
    STATE["building"] = True
    t0 = time.time()
    try:
        apps, games = _apps()
        settings = [{"name": k + " settings", "path": v, "kind": "setting"} for k, v in SETTINGS_PAGES.items()] + \
                   [{"name": k, "path": v, "kind": "control"} for k, v in CONTROL_PANEL.items()]
        files = _walk_files()
        data = {"built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "apps": apps, "games": games, "settings": settings, "files": files}
        tmp = IDX_PATH + ".tmp"
        with open(tmp, "w", encoding="utf8") as f:
            json.dump(data, f)
        os.replace(tmp, IDX_PATH)
        with _lock:
            STATE["data"] = data; STATE["built_at"] = time.time()
        log.info("index built in %.0fs: %d apps, %d games, %d settings, %d files", time.time() - t0, len(apps), len(games), len(settings), len(files))
        _embed_docs(data)
    except Exception:
        log.exception("index build")
    finally:
        STATE["building"] = False


def load():
    if STATE["data"] is None and os.path.exists(IDX_PATH):
        try:
            with open(IDX_PATH, encoding="utf8") as f:
                STATE["data"] = json.load(f)
            STATE["built_at"] = os.path.getmtime(IDX_PATH)
            _load_emb()
        except Exception:
            log.exception("index load")
    return STATE["data"]


def _loop():
    load()
    time.sleep(20)  # let Vex finish starting
    while True:
        if time.time() - STATE["built_at"] > REFRESH_H * 3600 or STATE["data"] is None:
            build()
        time.sleep(600)


def start_background():
    threading.Thread(target=_loop, daemon=True, name="pcindex").start()


def stats():
    d = load()
    if not d:
        return {"built": ""}
    fs = d["files"]
    return {"built": d["built"][-5:] if d["built"][:10] == datetime.date.today().isoformat() else d["built"], "apps": len(d["apps"]),
            "games": len(d["games"]), "settings": len(d["settings"]), "files": sum(1 for f in fs if f["kind"] == "file"),
            "docs": sum(1 for f in fs if f.get("text")), "semantic": STATE["emb"] is not None}


# ------------------------------------------------------------------ embeddings (optional)
def _embed_model():
    want = config.get("embed_model") or "nomic-embed-text"
    try:
        tags = json.loads(urllib.request.urlopen(config.get("ollama_url").rstrip("/") + "/api/tags", timeout=5).read())
        return next((m["name"] for m in tags.get("models", []) if m["name"].split(":")[0] == want), None)
    except Exception:
        return None


def _embed(texts, model):
    body = json.dumps({"model": model, "input": texts, "keep_alive": "1m"}).encode()
    req = urllib.request.Request(config.get("ollama_url").rstrip("/") + "/api/embed", body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["embeddings"]


def _embed_docs(data):
    model = _embed_model()
    if not model:
        return
    import numpy as np
    docs = [f for f in data["files"] if f.get("text")][:1500]
    vecs = []
    for i in range(0, len(docs), 16):
        chunk = docs[i:i + 16]
        try:
            vecs += _embed(["search_document: " + d["name"] + "\n" + d["text"][:1200] for d in chunk], model)
        except Exception as e:
            log.info("embed failed: %s", e); return
        time.sleep(0.2)
    m = np.array(vecs, dtype=np.float32)
    m /= (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
    np.save(EMB_PATH, m.astype(np.float16))
    with open(EMB_PATH + ".paths.json", "w", encoding="utf8") as f:
        json.dump([d["path"] for d in docs], f)
    STATE["emb"] = (m, [d["path"] for d in docs])
    log.info("embedded %d docs with %s", len(docs), model)


def _load_emb():
    try:
        import numpy as np
        if os.path.exists(EMB_PATH):
            STATE["emb"] = (np.load(EMB_PATH).astype(np.float32), json.load(open(EMB_PATH + ".paths.json", encoding="utf8")))
    except Exception:
        STATE["emb"] = None


# ------------------------------------------------------------------ search
def _name_score(q, name):
    from .resolve import score
    return score(q, os.path.splitext(name)[0])


def search_files(query, limit=8, folders=True):
    """Files/folders by name (fuzzy) + doc text (keywords) + meaning (embeddings if available)."""
    d = load()
    if not d:
        return []
    q = re.sub(r"\b(?:my|the|files?|folders?|docs?|documents?|stuff|project)\b", " ", query.lower()).strip()
    qt = set(toks(q))
    qn = re.sub(r"[^a-z0-9]", "", q)
    scores = {}
    for f in d["files"]:
        if f["kind"] == "folder" and not folders:
            continue
        nm = f["name"].lower()
        nn = re.sub(r"[^a-z0-9]", "", nm)
        s = 0.0
        if qn and qn in nn:
            s = 0.9 + (0.08 if nn.startswith(qn) else 0)
        elif qt:
            nt = set(toks(f["name"]))
            ov = len(qt & nt) / len(qt)
            s = ov * 0.8
            if s < 0.5 and len(qn) > 4:
                s = max(s, _name_score(q, f["name"]) * 0.85 if abs(len(nn) - len(qn)) < 12 else 0)
        if f.get("text") and qt:
            tt = set(toks(f["text"]))
            s = max(s, 0.55 * len(qt & tt) / len(qt))
        if f["kind"] == "folder":
            s += 0.03
        if s >= 0.45:
            scores[f["path"]] = (s, f)
    emb = STATE.get("emb")
    if emb and qt:
        try:
            import numpy as np
            model = _embed_model()
            if model:
                v = np.array(_embed(["search_query: " + query], model)[0], dtype=np.float32)
                v /= np.linalg.norm(v) + 1e-9
                sims = emb[0] @ v
                byp = {f["path"]: f for f in d["files"]}
                for i in np.argsort(-sims)[:10]:
                    p = emb[1][i]
                    if sims[i] > 0.55 and p in byp:
                        s = 0.45 + (float(sims[i]) - 0.55)
                        if p not in scores or scores[p][0] < s:
                            scores[p] = (s, byp[p])
        except Exception as e:
            log.info("semantic search: %s", e)
    out = sorted(scores.values(), key=lambda x: (-x[0], -(x[1].get("mtime") or 0)))
    return [dict(f, score=round(s, 2)) for s, f in out[:limit]]


def find_setting(q):
    """Best settings page / Control Panel item for a spoken phrase."""
    from .resolve import score
    ql = re.sub(r"\b(?:open|bring up|pull up|show me|the|my|windows|page|menu|options?)\b", " ", q.lower())
    ql = re.sub(r"\s+", " ", ql).strip()
    base = re.sub(r"\s*settings?$", "", ql).strip()
    best, bs = None, 0.0
    for k, v in list(SETTINGS_PAGES.items()) + list(CONTROL_PANEL.items()):
        s = max(score(base, k), score(ql, k), score(ql, k + " settings"))
        if s > bs:
            best, bs = (k, v), s
    return (best, bs) if best else (None, 0)


def open_setting(uri):
    import subprocess
    if uri.startswith(("ms-settings:", "windowsdefender:")) or uri.endswith((".cpl", ".msc")):
        os.startfile(uri)
    else:
        subprocess.Popen(uri if " " in uri else [uri], shell=" " in uri, creationflags=0x08000000)
