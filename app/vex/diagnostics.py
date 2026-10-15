"""Vex 3.4 'run a full scan': read-only snapshot of the PC for the cinematic scan view. Changes nothing."""
import os, time, socket, shutil, subprocess, ctypes, logging
from . import assist

log = logging.getLogger("vex.diag")
NOWIN = 0x08000000 if os.name == "nt" else 0


def _drives():
    out = []
    for L in "CDEFGHIJ":
        p = f"{L}:\\"
        if os.path.exists(p):
            try:
                u = shutil.disk_usage(p); out.append({"d": L, "used": round(u.used / u.total * 100), "free": round(u.free / 1e9), "total": round(u.total / 1e9)})
            except Exception: pass
    return out


def _procs():
    try:
        r = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=6, creationflags=NOWIN)
        rows = []
        for ln in r.stdout.splitlines():
            p = [x.strip('"') for x in ln.split('","')]
            if len(p) >= 5:
                try: rows.append((p[0], int(p[4].replace(",", "").replace(".", "").split()[0])))
                except Exception: pass
        agg = {}
        for n, k in rows: agg[n] = agg.get(n, 0) + k
        top = sorted(agg.items(), key=lambda x: -x[1])[:6]
        return len(rows), [{"name": n, "mb": round(k / 1024)} for n, k in top]
    except Exception:
        return 0, []


def _uptime():
    try: return int(ctypes.windll.kernel32.GetTickCount64() / 1000)
    except Exception: return 0


def _net():
    out = {"host": socket.gethostname()}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("10.255.255.255", 1)); out["ip"] = s.getsockname()[0]; s.close()
    except Exception: out["ip"] = "offline"
    t = time.time()
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=2).close(); out["latency"] = round((time.time() - t) * 1000)
    except Exception: out["latency"] = None
    return out


def scan():
    st = assist.pc_stats()
    n, top = _procs()
    d = {"cpu": st.get("cpu"), "ram": st.get("ram"), "ram_total": st.get("ram_total"), "gpu": st.get("gpu"), "gpu_name": st.get("gpu_name"),
         "gpu_temp": st.get("gpu_temp"), "vram": st.get("vram"), "drives": _drives(), "procs": n, "top": top, "uptime": _uptime(), "net": _net(),
         "net_down": st.get("net_down"), "net_up": st.get("net_up"), "at": time.strftime("%H:%M:%S")}
    warn = []
    if (d["ram"] or 0) > 88: warn.append("memory is running high")
    if (d["gpu_temp"] or 0) > 83: warn.append(f"GPU is hot at {d['gpu_temp']} degrees")
    for x in d["drives"]:
        if x["used"] > 92: warn.append(f"drive {x['d']} is {x['used']} percent full")
    if d["net"].get("latency") is None: warn.append("I can't reach the internet")
    d["warn"] = warn
    up = d["uptime"]; h = up // 3600
    d["say"] = ("Scan complete. All systems nominal. " if not warn else "Scan complete. Heads up: " + ", ".join(warn) + ". ") + \
        f"CPU at {d['cpu'] or 0} percent, memory {d['ram'] or 0} percent" + (f", GPU {d['gpu']} percent at {d['gpu_temp']} degrees" if d.get("gpu") is not None and d.get("gpu_temp") else "") + \
        (f", ping {d['net']['latency']} milliseconds" if d["net"].get("latency") is not None else "") + f". Up for {h} hour{'s' if h != 1 else ''}."
    log.info("diagnostics scan: cpu=%s ram=%s gpu=%s/%sC procs=%s warn=%s", d["cpu"], d["ram"], d["gpu"], d["gpu_temp"], n, warn)
    return d
