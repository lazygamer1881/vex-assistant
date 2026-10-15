"""Keeps Vex running: starts the app and restarts it if it crashes.
Quitting from the tray (clean exit, code 0) stops the watchdog too."""
import os, sys, time, ctypes, subprocess, logging
from . import config, winutil

SHOW_EVENT = "Local\\VexPublicShowWindow"


def signal_show():
    if winutil.IS_WIN:
        k = ctypes.windll.kernel32
        k.OpenEventW.restype = ctypes.c_void_p
        k.SetEvent.argtypes = [ctypes.c_void_p]; k.CloseHandle.argtypes = [ctypes.c_void_p]
        h = k.OpenEventW(0x0002, False, SHOW_EVENT)  # EVENT_MODIFY_STATE
        if h:
            k.SetEvent(h); k.CloseHandle(h)


def run(minimized):
    if not winutil.single_instance("Local\\VexPublicWatchdogSingleton"):
        if not minimized:
            signal_show()
        return
    log = logging.getLogger("vex.watchdog")
    pyw = os.path.join(config.APP_DIR, "python", "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    script = os.path.join(config.APP_DIR, "app", "run_vex.pyw")
    crashes = []
    first = True
    while True:
        args = [pyw, script, "--child"] + (["--minimized"] if (minimized or not first) else [])
        first = False
        t0 = time.time()
        p = subprocess.Popen(args, cwd=config.APP_DIR)
        code = p.wait()
        if code in (0, 3):  # 0 = quit from tray, 3 = another Vex already running
            log.info("vex exited (%s), watchdog stopping", code)
            return
        if code == 75:      # 4.3: restart asked for (e.g. after the voice pack download)
            log.info("restart requested")
            first = True; minimized = False
            continue
        try:
            from . import crashreport
            tail = ""
            lp = os.path.join(config.LOG_DIR, "vex.log")
            if os.path.exists(lp):
                with open(lp, encoding="utf-8", errors="replace") as f:
                    tail = "".join(f.readlines()[-25:])
            crashreport.write(f"app exited with code {code} after {time.time() - t0:.0f}s (restarted automatically)", extra="last log lines:\n" + tail)
        except Exception:
            pass
        log.warning("vex exited with code %s after %.0fs, restarting", code, time.time() - t0)
        now = time.time()
        crashes = [c for c in crashes if now - c < 600] + [now]
        if len(crashes) >= 5:
            log.error("vex crashed 5 times in 10 min, waiting 10 min before trying again")
            time.sleep(600); crashes = []
        else:
            time.sleep(min(30, 3 * len(crashes)))
