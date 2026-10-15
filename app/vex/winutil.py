"""Small Windows helpers using ctypes (no extra packages)."""
import os, sys, time, ctypes, threading
from ctypes import wintypes

IS_WIN = sys.platform == "win32"

if IS_WIN:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_MENU = 0x12
VK_CONTROL = 0x11
VK_BACK = 0x08
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
SW_RESTORE = 9
WM_CLOSE = 0x0010
GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080


def set_dpi_aware():
    if not IS_WIN:
        return
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def _proc_name(pid):
    h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return os.path.basename(buf.value)
        return ""
    finally:
        kernel32.CloseHandle(h)


def list_windows():
    """Visible, real app windows in z-order (top-most first): list of dicts."""
    if not IS_WIN:
        return []
    out = []
    my_pid = os.getpid()

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, GW_OWNER):
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value
        if title in ("Program Manager", "Windows Input Experience", "Settings", "Microsoft Text Input Application"):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        cloaked = ctypes.c_int(0)
        try:
            ctypes.windll.dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        except Exception:
            pass
        if cloaked.value:
            return True
        out.append({"hwnd": hwnd, "title": title, "pid": pid.value, "exe": _proc_name(pid.value), "mine": pid.value == my_pid})
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def find_windows(keys):
    """Windows whose exe or title matches any of the keys."""
    keys = [_norm(k) for k in keys if k]
    res = []
    for w in list_windows():
        if w["mine"]:
            continue
        exe = _norm(w["exe"].rsplit(".", 1)[0])
        title = _norm(w["title"])
        if any(k and (k == exe or k in exe or k in title) for k in keys):
            res.append(w)
    return res


def _press(vk, up=False):
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.u.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP if up else 0, time=0, dwExtraInfo=0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def tap_key(vk, times=1):
    if not IS_WIN:
        return
    for _ in range(times):
        _press(vk)
        _press(vk, up=True)
        time.sleep(0.02)


def focus_window(hwnd):
    if not IS_WIN:
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    # Tapping Alt lets a background app take focus (Windows foreground lock rule).
    _press(VK_MENU); _press(VK_MENU, up=True)
    ok = bool(user32.SetForegroundWindow(hwnd))
    time.sleep(0.15)
    return ok or user32.GetForegroundWindow() == hwnd


def foreground_window():
    if not IS_WIN:
        return None
    hwnd = user32.GetForegroundWindow()
    for w in list_windows():
        if w["hwnd"] == hwnd:
            return w
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {"hwnd": hwnd, "title": "", "pid": pid.value, "exe": _proc_name(pid.value), "mine": pid.value == os.getpid()}


def type_text(text, cancel=None):
    """Types unicode text into whatever has focus. Never presses Enter. Stops if cancel is set."""
    if not IS_WIN:
        return
    text = text.replace("\r", " ").replace("\n", " ")
    for ch in text:
        if cancel is not None and cancel.is_set():
            return
        code = ord(ch)
        units = [code] if code <= 0xFFFF else [0xD800 + ((code - 0x10000) >> 10), 0xDC00 + ((code - 0x10000) & 0x3FF)]
        for u in units:
            for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP):
                inp = INPUT(type=INPUT_KEYBOARD)
                inp.u.ki = KEYBDINPUT(wVk=0, wScan=u, dwFlags=flags, time=0, dwExtraInfo=0)
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.008)


def press_enter():
    tap_key(VK_RETURN)


def clear_typed(count):
    """Backspace `count` characters (used only to undo text Vex typed)."""
    tap_key(VK_BACK, times=max(0, count))


def work_area(hwnd):
    mon = user32.MonitorFromWindow(hwnd, 2)  # nearest
    mi = MONITORINFO(); mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(mon, ctypes.byref(mi))
    r = mi.rcWork
    return r.left, r.top, r.right, r.bottom


def snap_pair(left_hwnd, right_hwnd):
    if not IS_WIN:
        return
    l, t, r, b = work_area(left_hwnd)
    half = (r - l) // 2
    for hwnd, x in ((left_hwnd, l), (right_hwnd, l + half)):
        if user32.IsZoomed(hwnd) or user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.05)
        user32.SetWindowPos(hwnd, None, x, t, half, b - t, 0x0040 | 0x0004)  # SHOWWINDOW | NOZORDER
    focus_window(right_hwnd)
    focus_window(left_hwnd)


def close_window(hwnd):
    """Same as clicking the X button (the app can still ask to save)."""
    if IS_WIN:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def lock_screen():
    if IS_WIN:
        user32.LockWorkStation()


def single_instance(name="Local\\VexPublicSingleton"):
    if not IS_WIN:
        return True
    kernel32.CreateMutexW(None, False, name)
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS


# ---------------- global hotkey (RegisterHotKey, no keyboard hook) ----------------
MOD = {"alt": 0x1, "ctrl": 0x2, "control": 0x2, "shift": 0x4, "win": 0x8}


def parse_hotkey(s):
    mods, vk = 0, None
    for part in s.lower().replace(" ", "").split("+"):
        if part in MOD:
            mods |= MOD[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        elif part.startswith("f") and part[1:].isdigit():
            vk = 0x70 + int(part[1:]) - 1
        elif part == "space":
            vk = 0x20
    return mods | 0x4000, vk  # MOD_NOREPEAT


class Hotkey(threading.Thread):
    def __init__(self, combo, callback):
        super().__init__(daemon=True)
        self.combo, self.callback, self.ok = combo, callback, None
        self._tid = None

    def run(self):
        if not IS_WIN:
            return
        mods, vk = parse_hotkey(self.combo)
        if vk is None:
            self.ok = False
            return
        self._tid = kernel32.GetCurrentThreadId()
        self.ok = bool(user32.RegisterHotKey(None, 1, mods, vk))
        if not self.ok:
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                try:
                    self.callback()
                except Exception:
                    pass
        user32.UnregisterHotKey(None, 1)

    def stop(self):
        if IS_WIN and self._tid:
            user32.PostThreadMessageW(self._tid, 0x0012, 0, 0)  # WM_QUIT


def running_process_names():
    """Lower-case exe names of all running processes (Toolhelp snapshot, no extra packages)."""
    if not IS_WIN:
        return set()
    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    names = set()
    e = PROCESSENTRY32W(); e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        ok = kernel32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            names.add(e.szExeFile.lower())
            ok = kernel32.Process32NextW(snap, ctypes.byref(e))
    finally:
        kernel32.CloseHandle(snap)
    return names


# ---------------- general control helpers (used by pc.py) ----------------
SW_MINIMIZE, SW_MAXIMIZE = 6, 3
VK_MEDIA = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2}
KEYS = {"ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B, "windows": 0x5B, "enter": 0x0D, "return": 0x0D,
        "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "space": 0x20, "spacebar": 0x20, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
        "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
        "insert": 0x2D, "printscreen": 0x2C, "capslock": 0x14, "plus": 0xBB, "minus": 0xBD, "comma": 0xBC, "period": 0xBE}
EXTENDED = {0x26, 0x28, 0x25, 0x27, 0x24, 0x23, 0x21, 0x22, 0x2D, 0x2E, 0x5B}


def parse_combo(text):
    """'control shift s' / 'ctrl+s' / 'alt f4' -> list of VK codes, or None if a key is unknown."""
    t = text.lower().replace("+", " ").replace("-", " ").replace("page up", "pageup").replace("page down", "pagedown").replace("print screen", "printscreen")
    vks = []
    for part in t.split():
        if part in KEYS:
            vks.append(KEYS[part])
        elif len(part) == 1 and part.isalnum():
            vks.append(ord(part.upper()))
        elif part.startswith("f") and part[1:].isdigit() and 1 <= int(part[1:]) <= 12:
            vks.append(0x70 + int(part[1:]) - 1)
        elif part in ("key", "keys", "the", "press", "hit"):
            continue
        else:
            return None
    return vks or None


def send_combo(vks):
    if not IS_WIN:
        return
    def ev(vk, up):
        inp = INPUT(type=INPUT_KEYBOARD)
        flags = (KEYEVENTF_KEYUP if up else 0) | (0x0001 if vk in EXTENDED else 0)
        inp.u.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    for vk in vks:
        ev(vk, False)
    for vk in reversed(vks):
        ev(vk, True)


def show_window(hwnd, cmd):
    if IS_WIN:
        user32.ShowWindow(hwnd, cmd)


def click(x=None, y=None, button="left", double=False):
    if not IS_WIN:
        return
    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.05)
    down, up = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010), "middle": (0x0020, 0x0040)}[button]
    for _ in range(2 if double else 1):
        for flag in (down, up):
            inp = INPUT(type=0)
            inp.u.mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flag, time=0, dwExtraInfo=0)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.06)


def virtual_screen():
    """(left, top, width, height) of the whole multi-monitor desktop."""
    if not IS_WIN:
        return (0, 0, 1920, 1080)
    g = user32.GetSystemMetrics
    return g(76), g(77), g(78), g(79)


def mouse_button(down, button="left"):
    if not IS_WIN:
        return
    flag = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010)}[button][0 if down else 1]
    inp = INPUT(type=0)
    inp.u.mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flag, time=0, dwExtraInfo=0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def mouse_wheel(delta):
    if not IS_WIN:
        return
    inp = INPUT(type=0)
    inp.u.mi = MOUSEINPUT(dx=0, dy=0, mouseData=ctypes.c_ulong(int(delta) & 0xFFFFFFFF).value, dwFlags=0x0800, time=0, dwExtraInfo=0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def cursor_pos():
    if not IS_WIN:
        return (0, 0)
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def window_rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom
