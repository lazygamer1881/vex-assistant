"""Vex 4.2 dashboard tabs: data for the System and Activity tabs (local only, nothing saved)."""
import collections, os, time, logging

log = logging.getLogger(__name__)
ACT = collections.deque(maxlen=80)      # Vex's own replies / actions (never the user's words)
_nic = {"t": 0, "c": {}}


def note(text, kind="vex"):
    text = " ".join(str(text or "").split())
    if not text:
        return
    ACT.appendleft({"ts": time.time(), "t": time.strftime("%H:%M"), "kind": kind, "text": text[:180]})


def _procs(n=8):
    import psutil
    cores = psutil.cpu_count() or 1
    out = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            i = p.info
            nm = (i.get("name") or "").replace(".exe", "")
            if not nm or nm in ("System Idle Process", "Idle", "System", "Registry", "Memory Compression"):
                continue
            out.append({"name": nm[:28], "cpu": round((i.get("cpu_percent") or 0) / cores, 1),
                        "mem": round(((i.get("memory_info").rss if i.get("memory_info") else 0)) / 2**20)})
        except Exception:
            pass
    # merge same-name processes (browsers etc.)
    m = {}
    for x in out:
        y = m.setdefault(x["name"], {"name": x["name"], "cpu": 0, "mem": 0, "n": 0})
        y["cpu"] += x["cpu"]; y["mem"] += x["mem"]; y["n"] += 1
    L = sorted(m.values(), key=lambda x: (x["cpu"], x["mem"]), reverse=True)[:n]
    for x in L:
        x["cpu"] = round(x["cpu"], 1)
    return L, len(out)


def _drives():
    import psutil
    out = []
    for p in psutil.disk_partitions(all=False):
        if "cdrom" in (p.opts or "") or not p.fstype:
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
            out.append({"mount": p.mountpoint.rstrip("\\"), "fs": p.fstype, "pct": round(u.percent),
                        "used": round(u.used / 1e9), "total": round(u.total / 1e9), "free": round(u.free / 1e9)})
        except Exception:
            pass
    return out[:6]


def _net():
    import psutil
    now = time.time(); c = psutil.net_io_counters(pernic=True)
    st = {}
    try:
        st = psutil.net_if_stats()
    except Exception:
        pass
    prev, dt = _nic["c"], max(0.5, now - _nic["t"]) if _nic["t"] else 0
    out = []
    for name, v in c.items():
        s = st.get(name)
        if s is not None and not s.isup:
            continue
        if any(k in name.lower() for k in ("loopback", "pseudo", "isatap", "teredo")):
            continue
        d = u = 0
        if dt and name in prev:
            d = (v.bytes_recv - prev[name][0]) / dt / 1024; u = (v.bytes_sent - prev[name][1]) / dt / 1024
        out.append({"name": name[:26], "down": round(max(0, d)), "up": round(max(0, u)), "speed": getattr(s, "speed", 0) if s else 0,
                    "recv": round(v.bytes_recv / 1e9, 2), "sent": round(v.bytes_sent / 1e9, 2)})
    _nic["t"] = now; _nic["c"] = {k: (v.bytes_recv, v.bytes_sent) for k, v in c.items()}
    out.sort(key=lambda x: (x["down"] + x["up"], x["recv"]), reverse=True)
    return out[:4]


def system_data():
    from . import assist
    d = {"stats": {}, "procs": [], "drives": [], "net": [], "nproc": 0}
    try: d["stats"] = assist.pc_stats()
    except Exception: log.exception("tab stats")
    try:
        import psutil
        d["procs"], d["nproc"] = _procs()
        d["uptime"] = int(time.time() - psutil.boot_time())
        d["cores"] = psutil.cpu_count(logical=False) or 0; d["threads"] = psutil.cpu_count() or 0
        f = psutil.cpu_freq(); d["ghz"] = round(f.current / 1000, 2) if f else None
    except Exception:
        log.exception("tab procs")
    try: d["drives"] = _drives()
    except Exception: log.exception("tab drives")
    try: d["net"] = _net()
    except Exception: log.exception("tab net")
    return d


def activity_data():
    from . import product
    items = list(ACT)
    today = time.strftime("%Y-%m-%d ")
    for s in list(product.STEPS)[:30]:
        try:
            ts = time.mktime(time.strptime(today + s["t"], "%Y-%m-%d %H:%M:%S"))
            items.append({"ts": ts, "t": s["t"][:5], "kind": "task" if s.get("state") != "fail" else "fail", "text": s["text"]})
        except Exception:
            pass
    try:
        from . import ops
        feed = list(ops.FEED)[:12]
    except Exception:
        feed = []
    items.sort(key=lambda x: x["ts"], reverse=True)
    kinds = collections.Counter(x["kind"] for x in items)
    timers = 0
    try:
        from . import assist
        timers = len(assist.active_timers())
    except Exception:
        pass
    return {"items": items[:40], "feed": feed, "replies": kinds.get("vex", 0), "tasks": kinds.get("task", 0), "alerts": len(feed), "timers": timers}
