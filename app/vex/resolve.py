"""Vex 2.4: 'bring up / pull up / show me X' resolver.

Order: running windows -> Vex's known apps -> Start Menu shortcuts -> installed apps (Get-StartApps, incl. UWP)
-> Steam / Epic games -> websites -> files (last). Fuzzy matching handles misspellings.
"""
import os, re, glob, json, random, difflib, logging

from . import tools, pc, winutil

log = logging.getLogger("vex.resolve")
LAST = {"name": None, "kind": None}   # last-mentioned thing, for "bring this up" / "it" / "that"
PENDING = {"choice": None}            # {"app": fn, "file": fn, "name": str}

SITES = {"youtube": "https://www.youtube.com", "twitch": "https://www.twitch.tv", "roblox": "https://www.roblox.com/home",
         "reddit": "https://www.reddit.com", "gmail": "https://mail.google.com", "google": "https://www.google.com",
         "x": "https://x.com", "twitter": "https://x.com", "tiktok": "https://www.tiktok.com", "netflix": "https://www.netflix.com",
         "chatgpt": "https://chatgpt.com", "github": "https://github.com", "amazon": "https://www.amazon.com",
         "minecraft": "https://www.minecraft.net", "gorilla tag wiki": "https://gorillatag.fandom.com"}
VAGUE = re.compile(r"^(?:this|that|it|this up|that up|it up|this one|that one|the thing|the same thing|it again|that again)?$")
JUNK = re.compile(r"^(?:the|my|a|an|up)\s+|\s+(?:app|application|program|game|window|for me|please|again|on (?:my |the )?\w+ (?:monitor|screen))$")


def _n(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _clean(s):
    s = (s or "").lower().strip(" .!?,\"'")
    for _ in range(3):
        s = JUNK.sub("", s).strip()
    return s


def _ph(s):
    """Vex 4.2: rough sound-alike key so misheard names still match ('fortnight'->'fortnite', 'disc chord'->'discord')."""
    s = _n(s)
    for a, b in (("ph", "f"), ("ck", "k"), ("c", "k"), ("q", "k"), ("x", "ks"), ("z", "s"), ("ght", "t"), ("wh", "w"), ("dg", "j"), ("kh", "k")):
        s = s.replace(a, b)
    s = s[:1] + re.sub(r"[aeiouy]", "", s[1:])
    return re.sub(r"(.)\1+", r"\1", s)


def score(q, name):
    s = _score(q, name)
    if s < 0.9:
        a, b = _ph(q), _ph(name)
        if len(a) >= 3 and len(b) >= 3:
            s = max(s, difflib.SequenceMatcher(None, a, b).ratio() * 0.86)
    return s


def _score(q, name):
    """0..1 fuzzy score of spoken q against a name (handles 'capcut' vs 'cap cut', 'discrod', 'unity hub')."""
    a, b = _n(q), _n(name)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    words = [_n(w) for w in re.split(r"[\s\-_:.]+", name.lower()) if _n(w)]
    if a in words:
        return 0.93
    if b.startswith(a) and len(a) >= 3:
        return 0.9 - min(0.2, (len(b) - len(a)) / 60)
    if a in b and len(a) >= 4:
        return 0.8
    r = max([difflib.SequenceMatcher(None, a, b).ratio()] + [difflib.SequenceMatcher(None, a, w).ratio() for w in words])
    return r * 0.92


def _best(q, items, key):
    best, bs = None, 0.0
    for it in items:
        s = score(q, key(it))
        if s > bs:
            best, bs = it, s
    return best, bs


# ------------------------------------------------------------------ sources
def _windows(q):
    wins = [w for w in winutil.list_windows() if not w.get("mine")]
    key_, info = tools.resolve_app(q)
    if info and info.get("match"):
        for w in winutil.find_windows(info["match"]):
            exe = (w.get("exe") or "").rsplit(".", 1)[0]
            words = [_n(x) for x in re.split(r"[\s\-|:]+", w.get("title") or "")]
            if any(_n(m) == _n(exe) for m in info["match"]) or _n(info["label"]) in words or _n(q) in words:
                return w, 0.97
    best, bs = None, 0.0
    for w in wins:
        exe = (w.get("exe") or "").rsplit(".", 1)[0]
        title = w.get("title") or ""
        s = max(score(q, exe), score(q, title.split(" - ")[-1]) * 0.95, score(q, title) * 0.85)
        if s > bs:
            best, bs = w, s
    return best, bs


_games = {"items": None}


def _steam_games():
    out = []
    roots = [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            roots.insert(0, os.path.normpath(winreg.QueryValueEx(k, "SteamPath")[0]))
    except Exception:
        pass
    libs = set()
    for r in roots:
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            libs.add(os.path.join(r, "steamapps"))
            try:
                for p in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf8", errors="ignore").read()):
                    libs.add(os.path.join(p.replace("\\\\", "\\"), "steamapps"))
            except OSError:
                pass
    for lib in libs:
        for acf in glob.glob(os.path.join(lib, "appmanifest_*.acf")):
            try:
                txt = open(acf, encoding="utf8", errors="ignore").read()
                name = re.search(r'"name"\s+"([^"]+)"', txt).group(1)
                aid = re.search(r'"appid"\s+"(\d+)"', txt).group(1)
                if not re.search(r"redistributable|steamworks|proton|runtime", name, re.I):
                    out.append({"name": name, "uri": f"steam://rungameid/{aid}", "src": "Steam"})
            except Exception:
                pass
    return out


def _epic_games():
    out = []
    for f in glob.glob(r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests\*.item"):
        try:
            d = json.load(open(f, encoding="utf8"))
            uri = f"com.epicgames.launcher://apps/{d['CatalogNamespace']}%3A{d['CatalogItemId']}%3A{d['AppName']}?action=launch&silent=true"
            out.append({"name": d["DisplayName"], "uri": uri, "src": "Epic"})
        except Exception:
            pass
    return out


def games():
    if _games["items"] is None:
        seen, out = set(), []
        for g in _steam_games() + _epic_games():
            if g["name"] not in seen:
                seen.add(g["name"]); out.append(g)
        _games["items"] = out
    return _games["items"]


def _shortcuts():
    files = tools._shortcut_files()
    return [{"name": os.path.splitext(os.path.basename(f))[0], "path": f} for f in files]


# ------------------------------------------------------------------ resolve
def candidates(q):
    """Best candidate from each source: list of (score, kind, label, action)."""
    c = []
    w, s = _windows(q)
    if w and s >= 0.78:
        c.append((s + 0.05, "window", (w.get("title") or w.get("exe"))[:50], ("focus", w["hwnd"])))
    key, info = tools.resolve_app(q)
    if info and not info.get("shortcut"):
        c.append((0.96 if _n(q) in [_n(a) for a in info["aliases"]] else 0.85, "app", info["label"], ("app", q)))
    sc, s = _best(q, _shortcuts(), lambda x: x["name"])
    if sc and s >= 0.72:
        c.append((s, "app", sc["name"], ("start", sc["path"])))
    sa, s = _best(q, pc.start_apps(), lambda x: x["name"])
    if sa and s >= 0.72:
        c.append((s - 0.01, "app", sa["name"], ("start", "shell:AppsFolder\\" + sa["id"])))
    g, s = _best(q, games(), lambda x: x["name"])
    if g and s >= 0.72:
        c.append((s, "game", g["name"], ("start", g["uri"])))
    site, s = _best(q, [{"name": k} for k in SITES], lambda x: x["name"])
    if site and s >= 0.9:
        c.append((s - 0.12, "site", site["name"].title(), ("start", SITES[site["name"]])))
    elif re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)*\.(com|net|org|tv|gg|io|co|dev|app|me)", q.replace(" dot ", ".")):
        c.append((0.95, "site", q, ("start", "https://" + q.replace(" dot ", "."))))
    try:   # Windows settings pages / Control Panel (after apps, before files)
        from . import pcindex
        hit, s = pcindex.find_setting(q)
        wants = bool(re.search(r"\b(settings?|control panel|options)\b", q))
        if hit and s >= 0.85:
            c.append((s + (0.2 if wants else -0.1), "setting", hit[0], ("setting", hit[1])))
    except Exception:
        pass
    c.sort(key=lambda x: -x[0])
    return c


def _run(kind, label, action):
    LAST.update(name=label, kind=kind)
    how, arg = action
    if pc._dry():
        return f"[dry-run] {kind}: {label} ({how} {arg})"
    if how == "focus":
        winutil.focus_window(arg)
        return random.choice([f"{label} is up, sir.", f"Here's {label}.", f"Brought {label} to the front."])
    if how == "app":
        return tools.open_app(arg)
    if how == "setting":
        from . import pcindex
        pcindex.open_setting(arg)
        return f"Here are your {label} settings." if arg.startswith("ms-settings") else f"Opening {label}."
    os.startfile(arg)
    return random.choice([f"Opening {label}.", f"{label}, coming right up.", f"Pulling up {label}."])


def _file_hit(q):
    try:
        from . import pcindex
        h = pcindex.search_files(q, limit=1)
        if h and h[0]["score"] >= 0.6:
            return h[0]["path"]
    except Exception:
        pass
    hits = pc.find_files(q, limit=1, max_seconds=4)
    return hits[0] if hits else None


def bring_up(target):
    q = _clean(target)
    if VAGUE.match(q):
        if not LAST["name"]:
            return "Bring up what, sir? I'm not sure what we were talking about."
        q = _clean(LAST["name"])
    c = candidates(q)
    best = c[0] if c else None
    if best and best[0] >= 0.9:
        log.info("bring_up %r -> %s %s (%.2f)", q, best[1], best[2], best[0])
        return _run(*best[1:])
    f = _file_hit(q)
    if f and score(q, os.path.splitext(os.path.basename(f))[0]) < 0.88:
        f = None if best else f   # only a loose file match: prefer the app
    if best and f:   # weak app match and a file with that name: ask
        fname = os.path.basename(f)
        PENDING["choice"] = {"name": q, "app": lambda: _run(*best[1:]), "file": lambda: _open_file(f)}
        return f"Did you mean the app, {best[2]}, or the file, {fname}?"
    if best and best[0] >= 0.72:
        return _run(*best[1:])
    if f:
        return _open_file(f)
    return f"I couldn't find an app, game, site or file called {q}."


def _open_file(path):
    LAST.update(name=os.path.basename(path), kind="file")
    pc._last_found["items"] = [path]
    if pc._dry():
        return f"[dry-run] file: {path}"
    return pc.open_found(0)


def answer_choice(text):
    """Handles the reply to 'Did you mean the app or the file?'. Returns a reply or None."""
    ch = PENDING["choice"]
    if not ch:
        return None
    t = text.lower()
    PENDING["choice"] = None
    if re.search(r"\b(app|application|program|game|first)\b", t):
        return ch["app"]()
    if re.search(r"\b(file|document|second|the other)\b", t):
        return ch["file"]()
    if re.search(r"\b(neither|never ?mind|cancel|no)\b", t):
        return "Very good, I'll leave it."
    return None


def note(name, kind="thing"):
    if name:
        LAST.update(name=name, kind=kind)


