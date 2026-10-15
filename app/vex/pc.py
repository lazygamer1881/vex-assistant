"""General PC control for Vex: apps, windows, mouse/keyboard, files, info, screenshots, media, power.

Safety (enforced here, not by the AI model):
  * needs a spoken "yes" first: Recycle Bin, Enter in chat apps/browsers, closing apps that may have unsaved work,
    shutdown/restart/sign-out/sleep, non-read-only PowerShell, running scripts/installers
  * full access to every drive/folder; writes inside Windows / Program Files / ProgramData (or Vex's own program files) need "yes"
  * deleting = Recycle Bin and always needs "yes"; never buys, never signs in, never touches Streamlabs/OBS controls
  * every call is written to actions.log; "Vex stop" cancels
"""
import os, re, sys, glob, time, json, shutil, difflib, datetime, subprocess, threading, logging

from . import config, winutil, tools
from .actlog import logged, ask, blocked, CANCEL

log = logging.getLogger("vex.pc")
UP = config.USERPROFILE or os.path.expanduser("~")
NOWIN = 0x08000000 if os.name == "nt" else 0


def _dry():
    return tools.DRY_RUN


# ------------------------------------------------------------------ paths
def known_folders():
    od = os.path.join(UP, "OneDrive")
    def pick(name):
        for base in (od, UP):
            p = os.path.join(base, name)
            if os.path.isdir(p):
                return p
        return os.path.join(UP, name)
    k = {"desktop": pick("Desktop"), "documents": pick("Documents"), "downloads": os.path.join(UP, "Downloads"),
         "pictures": pick("Pictures"), "videos": os.path.join(UP, "Videos"), "music": os.path.join(UP, "Music"),
         "home": UP, "user folder": UP, "projects": os.path.join(UP, "Projects"), "mods": os.path.join(UP, "Projects"),
         "onedrive": od, "vex": config.APP_DIR,
         "screenshots": os.path.join(pick("Pictures"), "Screenshots"), "clips": os.path.join(UP, "Videos")}
    k["my documents"] = k["documents"]; k["download"] = k["downloads"]; k["my desktop"] = k["desktop"]
    k["program files"] = r"C:\Program Files"; k["program files x86"] = r"C:\Program Files (x86)"; k["windows"] = r"C:\Windows"
    k["appdata"] = os.path.join(UP, "AppData"); k["steam"] = r"C:\Program Files (x86)\Steam"
    k["gorilla tag"] = r"C:\Program Files (x86)\Steam\steam\steamapps\common\Gorilla Tag"
    for letter in "CDEFGHIJ":
        root = f"{letter}:\\"
        if os.path.exists(root):
            k[f"{letter.lower()} drive"] = root; k[f"drive {letter.lower()}"] = root
    return k


SEARCH_SKIP = {"appdata", "node_modules", ".git", "$recycle.bin", "__pycache__", "site-packages", ".cache", "vexassistant",
               "windows", "system volume information", "winsxs", "$windows.~bt", "programdata"}
SYSTEM_ROOTS = [r"c:\windows", r"c:\program files", r"c:\program files (x86)", r"c:\programdata", r"c:\recovery", r"c:\$recycle.bin"]


def _norm(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def protected_reason(path):
    """None if writing here is fine. Otherwise a short reason, and Vex asks for a spoken "yes" first."""
    p = _norm(path)
    for sr in SYSTEM_ROOTS:
        if p == _norm(sr) or p.startswith(_norm(sr) + os.sep):
            return "that's inside a Windows system folder"
    if re.match(r"^[a-z]:\\?$", p):
        return "that's a whole drive"
    vex_core = [os.path.join(config.APP_DIR, d) for d in ("python", "app", "ollama", "models")]
    if any(p == _norm(v) or p.startswith(_norm(v) + os.sep) for v in vex_core):
        return "that's part of my own program files"
    if p in {_norm(v) for v in known_folders().values()}:
        return "that's one of your main folders"
    return None


def can_write(path):
    return protected_reason(path) is None


def _clean_name(s):
    s = (s or "").strip().strip("\"'.,!? ")
    s = re.sub(r"^(?:the|my|a|an)\s+", "", s, flags=re.I)
    s = re.sub(r"\s+(?:file|folder|document|video|picture|photo|clip)$", "", s, flags=re.I)
    return s.strip()


def find_files(name, where=None, folders_only=False, limit=8, max_seconds=6):
    """Fuzzy search by file/folder name under the user's folders. Newest matches first."""
    q = _clean_name(name).lower()
    if not q:
        return []
    roots = [known_folders().get(where.lower().strip().replace(" folder", ""), where)] if where else \
        [known_folders()[k] for k in ("desktop", "documents", "downloads", "pictures", "videos", "music", "projects") if k in known_folders()] + [UP]
    seen, hits, t0, count = set(), [], time.time(), 0
    qn = re.sub(r"[^a-z0-9]", "", q)
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        depth0 = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            if CANCEL.is_set() or time.time() - t0 > max_seconds:
                break
            dirnames[:] = [d for d in dirnames if d.lower() not in SEARCH_SKIP and not d.startswith(".")]
            if dirpath.count(os.sep) - depth0 >= (1 if root == UP else 4 if re.match(r"^[A-Za-z]:\\?$", root) else 6):
                dirnames[:] = []
            entries = dirnames if folders_only else dirnames + filenames
            for e in entries:
                count += 1
                full = os.path.join(dirpath, e)
                if full in seen:
                    continue
                el = e.lower()
                stem = re.sub(r"[^a-z0-9]", "", os.path.splitext(el)[0])
                score = 0
                if el == q or os.path.splitext(el)[0] == q:
                    score = 100
                elif qn and stem == qn:
                    score = 95
                elif qn and stem.startswith(qn):
                    score = 80
                elif qn and qn in stem:
                    score = 60
                elif len(qn) > 3 and difflib.SequenceMatcher(None, qn, stem).ratio() > 0.8:
                    score = 50
                if score:
                    seen.add(full)
                    try: mt = os.path.getmtime(full)
                    except OSError: mt = 0
                    hits.append((score, mt, full))
    hits.sort(key=lambda h: (-h[0], -h[1]))
    return [h[2] for h in hits[:limit]]


def resolve_folder(spoken):
    s = _clean_name(spoken).lower().replace(" folder", "")
    kf = known_folders()
    if s in kf:
        return kf[s]
    if os.path.isabs(spoken) and os.path.isdir(spoken):
        return spoken
    if re.fullmatch(r"[a-z]", s):
        s = s + " drive"
    if s in kf:
        return kf[s]
    m = re.match(r"(.+?) (?:on|in) (?:my |the )?(desktop|documents|downloads|pictures|videos|music|[a-j] drive|program files|appdata)$", s)
    if m:
        hits = find_files(m.group(1), m.group(2), folders_only=True, limit=1)
        return hits[0] if hits else None
    hits = find_files(s, folders_only=True, limit=1)
    return hits[0] if hits else None


def resolve_file(spoken):
    s = spoken.strip().strip("\"'")
    if os.path.isabs(s) and os.path.exists(s):
        return s
    m = re.match(r"(.+?) (?:on|in|from) (?:my |the )?(desktop|documents|downloads|pictures|videos|music|projects|[a-j] drive|program files|appdata)$", _clean_name(s).lower())
    hits = find_files(m.group(1), m.group(2), limit=1) if m else find_files(s, limit=1)
    return hits[0] if hits else None


_last_found = {"items": []}


def _short(p):
    return p.replace(UP, "~")


# ------------------------------------------------------------------ open anything
_start_apps = {"items": None}


def start_apps():
    """Every app in the Start menu (incl. Store apps) via Get-StartApps, cached."""
    if _start_apps["items"] is None:
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"], capture_output=True,
                                 text=True, timeout=20, creationflags=NOWIN).stdout
            data = json.loads(out or "[]")
            _start_apps["items"] = [{"name": d["Name"], "id": d["AppID"]} for d in (data if isinstance(data, list) else [data])
                                    if "uninstall" not in d["Name"].lower()]
        except Exception:
            _start_apps["items"] = []
    return _start_apps["items"]


BUILTIN = {"settings": "ms-settings:", "windows settings": "ms-settings:", "calculator": "calc.exe", "notepad": "notepad.exe",
           "task manager": "taskmgr.exe", "paint": "mspaint.exe", "snipping tool": "ms-screenclip:", "control panel": "control.exe",
           "sound settings": "ms-settings:sound", "display settings": "ms-settings:display", "bluetooth": "ms-settings:bluetooth",
           "wifi settings": "ms-settings:network-wifi", "microsoft store": "ms-windows-store:", "xbox": "xbox:", "camera": "microsoft.windows.camera:",
           "recycle bin": "shell:RecycleBinFolder", "this pc": "shell:MyComputerFolder"}
RISKY_EXT = {".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi", ".reg", ".exe", ".scr", ".jar", ".wsf", ".hta"}


def _startfile(target):
    if _dry():
        return
    if target.endswith(".exe") and not os.path.isabs(target):
        subprocess.Popen([target], creationflags=0x00000008)
    else:
        os.startfile(target)


@logged
def open_anything(target):
    t = tools.FILLER.sub("", (target or "").strip().lower()).strip()
    tl = _clean_name(t).lower()
    if not tl:
        return "Open what?"
    # 1. Vex's known apps (Streamlabs, Steam, Discord, GT, ...)
    key, info = tools.resolve_app(t)
    if info and not info.get("shortcut"):
        return tools.open_app(t)
    # 2. URL / website
    if re.match(r"^(https?://|www\.)", tl) or re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)*\.(com|net|org|tv|gg|io|co|dev|app|me|us)(/.*)?$", tl.replace(" dot ", ".")):
        url = tl.replace(" dot ", ".")
        url = url if url.startswith("http") else "https://" + url
        _startfile(url)
        return f"Opening {url.split('//')[1].split('/')[0]}."
    # 3. built-in Windows things
    if tl in BUILTIN:
        _startfile(BUILTIN[tl])
        return f"Opening {tl}."
    # 4. known folders
    kf = known_folders()
    fname = tl.replace(" folder", "")
    if fname in kf and os.path.isdir(kf[fname]):
        _startfile(kf[fname])
        return f"Opened your {fname} folder."
    # 5. Desktop / Start menu shortcut, then any Start menu app (Store apps too)
    if info and info.get("shortcut"):
        return tools.open_app(t)
    apps = start_apps()
    names = {a["name"].lower(): a for a in apps}
    m = difflib.get_close_matches(tl, list(names), n=1, cutoff=0.75) or [n for n in names if n.startswith(tl + " ") or n == tl][:1]
    if m:
        a = names[m[0]]
        _startfile("shell:AppsFolder\\" + a["id"])
        return f"Opening {a['name']}."
    # 6. a file or folder by name
    path = resolve_file(t) or resolve_folder(t)
    if path:
        ext = os.path.splitext(path)[1].lower()
        if ext in RISKY_EXT:
            return ask(f"That's a program or script, {os.path.basename(path)}. Running it could change stuff. Say yes to run it.",
                       f"run {path}", lambda: _confirmed_open(path))
        _startfile(path)
        return f"Opened {os.path.basename(path)}."
    return f"I couldn't find anything called {t}."


@logged
def _confirmed_open(path):
    _startfile(path)
    return f"Running {os.path.basename(path)}."


# ------------------------------------------------------------------ windows
SAFE_TO_CLOSE = {"steam", "discord", "spotify", "explorer", "file explorer", "meta link", "steamvr", "calculator", "settings",
                 "gorilla tag", "task manager", "taskmgr", "systemsettings", "applicationframehost", "oculusclient", "vrmonitor"}
EDITOR_HINT = re.compile(r"(^\*|\*\s*[-–]|unsaved|untitled|not saved|\u25cf)", re.I)


def _target_windows(app):
    a = (app or "").lower().strip()
    if a in ("", "this", "this window", "current", "current window", "the window", "it", "that", "that window", "active window"):
        fg = winutil.foreground_window()
        return [fg] if fg and not fg.get("mine") else []
    key, info = tools.resolve_app(app)
    keys = (info.get("match") or [info["label"]]) if info else [app]
    wins = winutil.find_windows(keys)
    if not wins:
        wins = winutil.find_windows([_clean_name(app)])
    return wins


def _app_label(w):
    return (w.get("title") or w.get("exe") or "that window")[:60]


@logged
def window_action(app, action):
    action = (action or "").lower()
    wins = _target_windows(app)
    if not wins:
        return f"I don't see {app or 'a window'} open."
    w = wins[0]
    if action == "close":
        exe = (w.get("exe") or "").lower().rsplit(".", 1)[0]
        key, info = tools.resolve_app(app) if app else (None, None)
        safe = (key in SAFE_TO_CLOSE or exe in SAFE_TO_CLOSE) and not EDITOR_HINT.search(w.get("title", ""))
        if not safe:
            label = _app_label(w)
            return ask(f"Closing {label} could lose unsaved work. Say yes to close it.", f"close window '{label}'",
                       lambda: _close_windows([x["hwnd"] for x in wins], label))
        return _close_windows([x["hwnd"] for x in wins], _app_label(w))
    if _dry():
        return f"[dry-run] would {action} '{_app_label(w)}'"
    if action in ("minimize", "minimise", "hide"):
        winutil.show_window(w["hwnd"], winutil.SW_MINIMIZE); return "Minimized it."
    if action in ("maximize", "maximise", "full screen", "fullscreen"):
        winutil.show_window(w["hwnd"], winutil.SW_MAXIMIZE); winutil.focus_window(w["hwnd"]); return "Maximized it."
    if action == "restore":
        winutil.show_window(w["hwnd"], winutil.SW_RESTORE); return "Restored it."
    if action in ("focus", "switch", "show", "bring up"):
        winutil.focus_window(w["hwnd"]); return f"Pulled up {_app_label(w)}."
    return f"I can close, minimize, maximize, or focus windows, not {action}."


@logged
def _close_windows(hwnds, label):
    if _dry():
        return f"[dry-run] would close '{label}'"
    for h in hwnds:
        winutil.close_window(h)
    return f"Closed {label}."


@logged
def minimize_all():
    if _dry():
        return "[dry-run] would show desktop"
    winutil.send_combo([0x5B, ord("D")]); return "Showing your desktop."


# ------------------------------------------------------------------ mouse + keyboard (focused window only)
CHAT_APPS = re.compile(r"discord|slack|teams|whatsapp|telegram|messenger|signal|outlook|thunderbird|mail|skype|instagram|snapchat|tiktok|twitter|x\.com|reddit|youtube studio|twitch", re.I)
BROWSERS = re.compile(r"chrome|msedge|firefox|opera|brave|vivaldi", re.I)
NO_TOUCH = re.compile(r"streamlabs|obs64|obs studio", re.I)
SHOP = re.compile(r"checkout|purchase|payment|buy now|place order|shopping cart|\bcart\b|billing|add funds|wallet|robux|v-bucks|shiny rocks", re.I)
SIGNIN = re.compile(r"sign in|signin|log in|login|password|verify it's you|two-factor|2fa|authenticator", re.I)


def _fg_guard(kind):
    fg = winutil.foreground_window() or {}
    t = (fg.get("title") or "") + " " + (fg.get("exe") or "")
    if fg.get("mine"):
        return fg, blocked("My own window's in front. Click the app you want first.")
    if NO_TOUCH.search(t):
        return fg, blocked("I don't press stuff in Streamlabs or OBS, that's how streams get started by accident.")
    if SHOP.search(t):
        return fg, blocked("That looks like a store or checkout page. I don't click or type there, buying is all you.")
    if kind == "type" and SIGNIN.search(t):
        return fg, blocked("That looks like a sign-in page. I don't type there, you got that one.")
    return fg, None


@logged
def type_into_focused(text):
    text = (text or "").replace("\n", " ").strip()
    if not text:
        return "Type what?"
    fg, b = _fg_guard("type")
    if b:
        return b
    if _dry():
        return f"[dry-run] would type into '{_app_label(fg)}': {text}"
    winutil.type_text(text, cancel=CANCEL)
    sends = CHAT_APPS.search((fg.get("title") or "") + (fg.get("exe") or "")) or BROWSERS.search(fg.get("exe") or "")
    if sends:
        label = _app_label(fg)
        return ask("Typed it. Say send to post it.", f"press Enter to send typed text in '{label}'", lambda: _send_keys([0x0D], label))
    return "Typed it."


def _is_enter(vks):
    return 0x0D in vks


@logged
def press_keys(combo):
    vks = winutil.parse_combo(combo or "")
    if not vks:
        return f"I don't know the key {combo}."
    if set(vks) >= {0x11, 0x12, 0x2E}:
        return blocked("Can't press control alt delete, Windows doesn't let apps do that.")
    fg, b = _fg_guard("keys")
    if b:
        return b
    label = _app_label(fg)
    t = (fg.get("title") or "") + " " + (fg.get("exe") or "")
    if vks == [0x12, 0x73]:  # alt+f4 = close the window
        exe = (fg.get("exe") or "").lower().rsplit(".", 1)[0]
        if exe not in SAFE_TO_CLOSE or EDITOR_HINT.search(fg.get("title", "")):
            return ask(f"Alt F4 closes {label}, could lose unsaved work. Say yes to do it.", f"alt+f4 on '{label}'", lambda: _send_keys(vks, label))
    if _is_enter(vks) and (CHAT_APPS.search(t) or BROWSERS.search(fg.get("exe") or "")):
        return ask(f"Pressing Enter in {label} might send or post something. Say yes to press it.", f"press {combo} in '{label}'",
                   lambda: _send_keys(vks, label))
    if 0x2E in vks and re.search(r"explorer", fg.get("exe") or "", re.I):
        return ask(f"That would delete the selected files in {label}. Say yes to do it.", f"press {combo} in File Explorer", lambda: _send_keys(vks, label))
    return _send_keys(vks, label)


@logged
def _send_keys(vks, label):
    if _dry():
        return f"[dry-run] would press {vks} in '{label}'"
    winutil.send_combo(vks)
    return "Done."


@logged
def mouse_click(button="left", double=False, x=None, y=None, where=None):
    fg, b = _fg_guard("click")
    if b:
        return b
    if where in ("center", "middle") and fg.get("hwnd"):
        l, t, r, btm = winutil.window_rect(fg["hwnd"])
        x, y = (l + r) // 2, (t + btm) // 2
    if _dry():
        return f"[dry-run] would {'double ' if double else ''}{button} click at {(x, y) if x is not None else 'the cursor'} in '{_app_label(fg)}'"
    winutil.click(x, y, button, double)
    return "Clicked."


@logged
def media(action):
    vk = winutil.VK_MEDIA.get(action)
    if not vk:
        return "I can play, pause, skip, or go back."
    if _dry():
        return f"[dry-run] media {action}"
    winutil.tap_key(vk)
    return {"play_pause": "Done.", "next": "Skipped.", "previous": "Went back.", "stop": "Stopped the music."}[action]


# ------------------------------------------------------------------ files (writes only inside the user folder)
@logged
def find(name, where=None):
    hits = []
    if not where:
        try:
            from . import pcindex
            hits = [h["path"] for h in pcindex.search_files(name, limit=8)]
        except Exception:
            hits = []
    if not hits:
        hits = find_files(name, where)
    _last_found["items"] = hits
    if not hits:
        return f"Couldn't find anything called {name}."
    first = os.path.basename(hits[0])
    where_txt = _short(os.path.dirname(hits[0]))
    more = f" and {len(hits) - 1} more" if len(hits) > 1 else ""
    return {"say": f"Found {first} in {where_txt}{more}. Say open it to open it.", "detail": "\n".join(_short(h) for h in hits)}


@logged
def open_found(index=0):
    items = _last_found["items"]
    if not items or index >= len(items):
        return "I don't have anything found yet. Say find and the name."
    p = items[index]
    if os.path.splitext(p)[1].lower() in RISKY_EXT:
        return ask(f"{os.path.basename(p)} is a program or script. Say yes to run it.", f"run {p}", lambda: _confirmed_open(p))
    _startfile(p)
    return f"Opened {os.path.basename(p)}."


@logged
def show_in_folder(name):
    p = resolve_file(name) or resolve_folder(name)
    if not p:
        return f"Couldn't find {name}."
    if not _dry():
        subprocess.Popen(["explorer", "/select,", p])
    return f"Showing {os.path.basename(p)} in File Explorer."


def _guarded(paths, say_ok, desc, fn):
    """Runs fn now, or asks for a spoken yes first if any path is protected."""
    reasons = [r for r in (protected_reason(p) for p in paths) if r]
    if reasons:
        return ask(f"Heads up, {reasons[0]}. {say_ok} Say yes to do it.", desc, fn)
    return fn()


@logged
def create_folder(name, where="desktop"):
    parent = resolve_folder(where or "desktop")
    if not parent:
        return f"I couldn't find the {where} folder."
    name = re.sub(r'[<>:"/\\|?*]', "", _clean_name(name)).strip() or "New folder"
    target = os.path.join(parent, name)
    if os.path.exists(target):
        return f"There's already a {name} there."
    return _guarded([target], f"I'm about to make a folder {name} in {_short(parent)}.", f"create folder {target}", lambda: _do_mkdir(target, parent))


@logged
def _do_mkdir(target, parent):
    if _dry():
        return f"[dry-run] would create {target}"
    os.makedirs(target)
    return f"Made a folder called {os.path.basename(target)} in {os.path.basename(parent.rstrip(os.sep)) or parent}."


def _dest_path(src, dest_folder):
    return os.path.join(dest_folder, os.path.basename(src.rstrip(os.sep)))


@logged
def move_item(name, to):
    src, dst_dir = resolve_file(name) or resolve_folder(name), resolve_folder(to)
    if not src:
        return f"Couldn't find {name}."
    if not dst_dir:
        return f"Couldn't find the {to} folder."
    dst = _dest_path(src, dst_dir)
    if os.path.exists(dst):
        return f"There's already a {os.path.basename(dst)} in {os.path.basename(dst_dir)}, I won't overwrite it."
    if _norm(dst).startswith(_norm(src) + os.sep):
        return "Can't move a folder into itself."
    return _guarded([src, dst], f"I'm about to move {_short(src)} to {_short(dst_dir)}.", f"move {src} -> {dst}", lambda: _do_move(src, dst, dst_dir))


@logged
def _do_move(src, dst, dst_dir):
    if _dry():
        return f"[dry-run] would move {_short(src)} -> {_short(dst)}"
    shutil.move(src, dst)
    return f"Moved {os.path.basename(src)} to {os.path.basename(dst_dir.rstrip(os.sep)) or dst_dir}."


@logged
def copy_item(name, to):
    src, dst_dir = resolve_file(name) or resolve_folder(name), resolve_folder(to)
    if not src:
        return f"Couldn't find {name}."
    if not dst_dir:
        return f"Couldn't find the {to} folder."
    dst = _dest_path(src, dst_dir)
    if os.path.exists(dst):
        return f"{os.path.basename(dst)} is already in {os.path.basename(dst_dir)}."
    return _guarded([dst], f"I'm about to copy {_short(src)} into {_short(dst_dir)}.", f"copy {src} -> {dst}", lambda: _do_copy(src, dst, dst_dir))


@logged
def _do_copy(src, dst, dst_dir):
    if _dry():
        return f"[dry-run] would copy {_short(src)} -> {_short(dst)}"
    if os.path.isdir(src):
        def ign(d, files):
            return files if CANCEL.is_set() else []  # "Vex stop" stops copying the rest
        shutil.copytree(src, dst, ignore=ign)
    else:
        shutil.copy2(src, dst)
    return "Stopped copying partway." if CANCEL.is_set() else f"Copied {os.path.basename(src)} to {os.path.basename(dst_dir.rstrip(os.sep)) or dst_dir}."


@logged
def rename_item(name, new_name):
    src = resolve_file(name) or resolve_folder(name)
    if not src:
        return f"Couldn't find {name}."
    new_name = re.sub(r'[<>:"/\\|?*]', "", (new_name or "").strip().strip("\"'"))
    if not new_name:
        return "Rename it to what?"
    if os.path.isfile(src) and not os.path.splitext(new_name)[1]:
        new_name += os.path.splitext(src)[1]  # keep the extension
    dst = os.path.join(os.path.dirname(src), new_name)
    if os.path.exists(dst):
        return f"Something's already called {new_name} there."
    return _guarded([src, dst], f"I'm about to rename {_short(src)} to {new_name}.", f"rename {src} -> {new_name}", lambda: _do_rename(src, dst))


@logged
def _do_rename(src, dst):
    if _dry():
        return f"[dry-run] would rename {_short(src)} -> {os.path.basename(dst)}"
    os.rename(src, dst)
    return f"Renamed it to {os.path.basename(dst)}."


@logged
def recycle_item(name):
    src = resolve_file(name) or resolve_folder(name)
    if not src:
        return f"Couldn't find {name}."
    why = protected_reason(src)
    warn = f"Careful, {why}. " if why else ""
    return ask(f"{warn}I'm about to put {os.path.basename(src.rstrip(os.sep)) or src} from {_short(os.path.dirname(src))} in the Recycle Bin. Say yes to do it.",
               f"recycle {src}", lambda: _recycle(src))


@logged
def _recycle(path):
    if _dry():
        return f"[dry-run] would move {_short(path)} to the Recycle Bin"
    kind = "DeleteDirectory" if os.path.isdir(path) else "DeleteFile"
    ps = ("Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::"
          f"{kind}('{path.replace(chr(39), chr(39) * 2)}', 'OnlyErrorDialogs', 'SendToRecycleBin')")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60, creationflags=NOWIN)
    if os.path.exists(path):
        return "Couldn't move it to the Recycle Bin."
    return f"Put {os.path.basename(path)} in the Recycle Bin. You can restore it from there."


# ------------------------------------------------------------------ screenshot
@logged
def screenshot():
    folder = os.path.join(known_folders()["pictures"], "Vex Screenshots")
    path = os.path.join(folder, f"screenshot-{datetime.datetime.now():%Y%m%d-%H%M%S}.png")
    if _dry():
        return f"[dry-run] would save {path}"
    from PIL import ImageGrab
    os.makedirs(folder, exist_ok=True)
    ImageGrab.grab(all_screens=True).save(path)
    return {"say": "Screenshot saved to Pictures, Vex Screenshots.", "detail": path}


# ------------------------------------------------------------------ power (always asks, 30 s countdown, cancellable)
# Only ever started by the user saying/typing the command AND then saying/tapping yes. Never from memory or automations.
POWER = {"shutdown": (["shutdown", "/s", "/t", "30", "/c", "Vex: shutting down in 30 seconds. Say cancel or Vex stop to abort."], "shut down the PC"),
         "restart": (["shutdown", "/r", "/t", "30", "/c", "Vex: restarting in 30 seconds. Say cancel or Vex stop to abort."], "restart the PC"),
         "sign_out": (["shutdown", "/l"], "sign you out of Windows"),
         "sleep": (["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], "put the PC to sleep"),
         "lock": (["rundll32.exe", "user32.dll,LockWorkStation"], "lock the PC")}
COUNTDOWN = 30
_PW = {"action": None, "ev": None, "t": None}


def _toast(text):
    try:
        from . import ops
        if ops.core:
            ops.core.emit("notify", {"title": "Vex power", "text": text})
            ops.feed("power", text)
    except Exception:
        pass


def power_pending():
    return _PW["action"]


@logged
def power(action):
    if action not in POWER:
        return "I can shut down, restart, sign out, sleep, or lock the PC."
    if _PW["action"]:
        return f"There's already a {_PW['action'].replace('_', ' ')} counting down. Say cancel to stop it."
    desc = POWER[action][1]
    return ask(f"You want me to {desc}. Save your stuff first. Shall I proceed?", desc, lambda: _power(action))


@logged
def _power(action):
    cmd, desc = POWER[action]
    if _dry():
        return f"[dry-run] would start a {COUNTDOWN}-second countdown, then run {' '.join(cmd[:4])}"
    ev = threading.Event()
    _PW.update(action=action, ev=ev, t=time.time())
    if action in ("shutdown", "restart"):
        subprocess.Popen(cmd, creationflags=NOWIN)  # Windows' own 30 s timer; 'shutdown /a' aborts it

    def run():
        for left in range(COUNTDOWN, 0, -1):
            if ev.is_set() or CANCEL.is_set():
                return
            if left in (COUNTDOWN, 10, 5):
                _toast(f"{desc[0].upper() + desc[1:]} in {left} seconds. Say cancel or Vex stop to abort.")
            time.sleep(1)
        if ev.is_set() or CANCEL.is_set():
            return
        _PW.update(action=None, ev=None)
        if action not in ("shutdown", "restart"):
            subprocess.Popen(cmd, creationflags=NOWIN)
    threading.Thread(target=run, daemon=True, name="vex-power").start()
    return f"Right. I'll {desc} in {COUNTDOWN} seconds. Say cancel to stop it."


@logged
def cancel_power(quiet=False):
    """'cancel shutdown' / 'cancel' / 'Vex stop': aborts any countdown (and any Windows shutdown timer)."""
    act = _PW["action"]
    if _PW["ev"]:
        _PW["ev"].set()
    _PW.update(action=None, ev=None)
    if _dry():
        return "[dry-run] would run shutdown /a and stop the countdown"
    try:
        subprocess.run(["shutdown", "/a"], capture_output=True, timeout=10, creationflags=NOWIN)
    except Exception:
        pass
    if act:
        _toast(f"Cancelled: {POWER[act][1]}.")
        return f"Cancelled. I won't {POWER[act][1]}."
    return "" if quiet else "Nothing was counting down, but I've cancelled any pending Windows shutdown just in case."


# ------------------------------------------------------------------ info + PowerShell
def _ps(cmd, timeout=20):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, text=True,
                       timeout=timeout, creationflags=NOWIN)
    return (r.stdout or "").strip(), (r.stderr or "").strip()


@logged
def system_info(topic):
    t = (topic or "").lower()
    if "batter" in t:
        out, _ = _ps("(Get-CimInstance Win32_Battery | Select -First 1).EstimatedChargeRemaining")
        return f"Battery's at {out} percent." if out.strip().isdigit() else "This PC doesn't have a battery, it's a desktop."
    if any(k in t for k in ("disk", "storage", "space", "drive")):
        du = shutil.disk_usage("C:\\" if os.name == "nt" else "/")
        return f"You got {du.free / 1e9:.0f} gigs free out of {du.total / 1e9:.0f} on C."
    if any(k in t for k in ("ram", "memory")):
        out, _ = _ps("$o=Get-CimInstance Win32_OperatingSystem; '{0:N0} {1:N0}' -f ($o.FreePhysicalMemory/1MB), ($o.TotalVisibleMemorySize/1MB)")
        free, total = (out.split() + ["?", "?"])[:2]
        return f"{free} of {total} gigs of RAM free."
    if "cpu" in t or "processor" in t:
        out, _ = _ps("[int](Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average")
        return f"CPU's at {out} percent."
    if "gpu" in t or "graphics" in t or "temp" in t:
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=5, creationflags=NOWIN).stdout.split(",")
            return f"GPU's at {out[0].strip()} degrees, {out[1].strip()} percent busy, {int(out[2]) / 1024:.1f} of {int(out[3]) / 1024:.0f} gigs VRAM used."
        except Exception:
            return "Couldn't read the GPU."
    if any(k in t for k in ("running", "open", "apps", "programs", "windows")):
        names = []
        for w in winutil.list_windows():
            if not w["mine"]:
                n = os.path.splitext(w["exe"])[0] or w["title"]
                if n and n not in names:
                    names.append(n)
        return ("You got " + ", ".join(names[:8]) + " open.") if names else "Nothing's open."
    if "uptime" in t or "been on" in t:
        out, _ = _ps("$u=(Get-Date)-(gcim Win32_OperatingSystem).LastBootUpTime; '{0}h {1}m' -f [int]$u.TotalHours, $u.Minutes")
        return f"PC's been on for {out}."
    if "ip" in t or "internet" in t or "wifi" in t or "network" in t:
        out, _ = _ps("(Test-Connection 1.1.1.1 -Count 1 -ErrorAction SilentlyContinue).ResponseTime")
        return f"Internet's up, {out} millisecond ping." if out else "Looks like the internet's down."
    return "I can check battery, disk space, RAM, CPU, GPU, what's running, uptime, or your internet."


READ_VERBS = ("get-", "measure-", "select-", "sort-", "where-", "format-", "out-string", "test-path", "test-connection", "resolve-path",
              "group-", "convertto-", "compare-", "find-", "hostname", "whoami", "ipconfig", "systeminfo", "tasklist", "nvidia-smi",
              "dir", "ls", "gci", "gps", "ps", "cat", "type", "gcim", "gwmi", "select", "sort", "where", "ft", "fl", "measure")
NOT_READ = re.compile(r"\b(set|new|remove|rm|del|erase|rd|rmdir|move|mv|copy|cp|rename|ren|clear|start|stop|restart|invoke|iex|enable|disable|"
                      r"install|uninstall|add|import|export|out-file|tee|write|update|register|unregister|suspend|resume|kill|format-volume|"
                      r"mount|dismount|initialize|reset|grant|revoke|push|pop|send|connect|disconnect)\b|>|\.delete\(|\.kill\(|\.terminate\(", re.I)
DANGER_PS = re.compile(r"\b(remove-item|rm|del|erase|rd|rmdir|format-volume|format|diskpart|bcdedit|cipher|vssadmin|takeown|icacls|"
                       r"clear-disk|reg\s+delete|set-executionpolicy|net\s+user|stop-computer|restart-computer|shutdown|"
                       r"invoke-expression|iex|downloadstring|invoke-webrequest|iwr|invoke-restmethod|irm)\b|c:\\windows|program files|programdata|hklm:|hkey_local_machine", re.I)
NEVER_PS = re.compile(r"\b(start-?stream|start-?recording|startstreaming|startrecording|purchase|checkout)\b", re.I)


def ps_is_read_only(cmd):
    if NOT_READ.search(cmd) or re.search(r"[;&`]|\$\(|\|\|", cmd):
        return False
    for seg in cmd.split("|"):
        first = seg.strip().split(" ")[0].lower() if seg.strip() else ""
        if not first or not any(first == v or (v.endswith("-") and first.startswith(v)) for v in READ_VERBS):
            return False
    return True


@logged
def run_powershell(command, purpose=""):
    cmd = (command or "").strip()
    if not cmd:
        return "Run what?"
    if NEVER_PS.search(cmd):
        return blocked("I don't start streams, recordings, or buy stuff, that's all you.")
    if ps_is_read_only(cmd):
        return _run_ps(cmd)
    if re.search(r"(?i)\b(remove-item|rm|del|erase|rd|rmdir)\b", cmd) and re.search(
            r"(?i)(program ?files|programfiles|\\windows|systemroot|windir|system32|programdata|\*\.exe|\*\.dll|-recurse[^|]*c:\\?\s*$|c:\\\*)", cmd):
        return blocked("I won't delete things in Program Files, Windows or ProgramData, or mass-delete programs. "
                       "Say 'clean up my disk' and I'll clear temp files and caches safely, or uninstall a game from its launcher.")
    if DANGER_PS.search(cmd):
        return ask(f"Careful, this one can delete stuff or change system settings: {cmd[:140]}. Say yes to run it.", f"powershell (dangerous): {cmd}", lambda: _run_ps(cmd))
    return ask(f"That command changes stuff on your PC: {cmd[:140]}. Say yes to run it.", f"powershell: {cmd}", lambda: _run_ps(cmd))


@logged
def _run_ps(cmd):
    if _dry():
        return f"[dry-run] would run PowerShell: {cmd}"
    try:
        out, err = _ps(cmd, timeout=25)
    except subprocess.TimeoutExpired:
        return "That took too long, I stopped it."
    text = out or err or "Done, no output."
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    spoken = "; ".join(lines[:3])[:220]
    return {"say": spoken if len(lines) <= 3 else spoken + ". Full output's in the transcript.", "detail": text[:3000]}


SAFE_CLEAN = [r"%TEMP%", r"%LOCALAPPDATA%\CrashDumps", r"%LOCALAPPDATA%\D3DSCache", r"%LOCALAPPDATA%\NVIDIA\DXCache", r"%LOCALAPPDATA%\NVIDIA\GLCache",
              r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache", r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache",
              r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache", r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache"]


def _clean_disk_now():
    import shutil
    before = shutil.disk_usage("C:\\").free
    for p in SAFE_CLEAN:
        d = os.path.expandvars(p)
        if not os.path.isdir(d) or "vexassistant" in d.lower():
            continue
        for n in os.listdir(d):
            f = os.path.join(d, n)
            try:
                shutil.rmtree(f) if os.path.isdir(f) and not os.path.islink(f) else os.remove(f)
            except Exception:
                pass  # in use
    freed = (shutil.disk_usage("C:\\").free - before) / 1e9
    return f"Done. Cleared temp files and caches, freeing about {max(freed, 0):.1f} GB. You now have {shutil.disk_usage('C:\\').free / 1e9:.0f} GB free. The big ones are CapCut's cache, Epic games and Minecraft, which are yours to decide on."


def clean_disk():
    return ask("I can clear temp files, crash dumps, shader caches and browser caches. No cookies, passwords or personal files. Shall I proceed?",
               "safe disk cleanup (temp + caches)", _clean_disk_now)
