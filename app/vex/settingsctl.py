"""Vex 2.6: read Windows settings states (read-only) and make a few changes ONLY after a yes (existing confirm system)."""
import re, subprocess, logging

log = logging.getLogger("vex.settings")
NOWIN = 0x08000000

VOL_PS = r'''
Add-Type -TypeDefinition @"
using System;using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume{int f();int g();int h();int i();int SetMasterVolumeLevelScalar(float l,Guid c);int j();int GetMasterVolumeLevelScalar(out float l);int k();int l2();int m();int n();int SetMute(bool b,Guid c);int GetMute(out bool b);}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice{int Activate(ref Guid id,int ctx,IntPtr p,[MarshalAs(UnmanagedType.IUnknown)] out object o);}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator{int f();int GetDefaultAudioEndpoint(int flow,int role,out IMMDevice d);}
[ComImport,Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumerator{}
public class VexVol{public static string Get(){var e=(IMMDeviceEnumerator)(new MMDeviceEnumerator());IMMDevice d;e.GetDefaultAudioEndpoint(0,1,out d);
var g=typeof(IAudioEndpointVolume).GUID;object o;d.Activate(ref g,23,IntPtr.Zero,out o);var v=(IAudioEndpointVolume)o;float l;v.GetMasterVolumeLevelScalar(out l);bool m;v.GetMute(out m);
return ((int)Math.Round(l*100)).ToString()+"|"+m.ToString();}}
"@
[VexVol]::Get()
'''


def _run(args, timeout=15):
    try:
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=NOWIN).stdout.strip()
    except Exception as e:
        return ""


def _ps(cmd, timeout=20):
    return _run(["powershell", "-NoProfile", "-Command", cmd], timeout)


def volume():
    out = _ps(VOL_PS)
    m = re.search(r"(\d+)\|(True|False)", out)
    return (int(m.group(1)), m.group(2) == "True") if m else (None, None)


def default_output():
    try:
        import sounddevice as sd
        for i, h in enumerate(sd.query_hostapis()):
            if "WASAPI" in h["name"] and h.get("default_output_device", -1) >= 0:
                return sd.query_devices(h["default_output_device"])["name"]
        return sd.query_devices(kind="output")["name"]
    except Exception:
        return None


def display():
    out = _ps("Get-CimInstance Win32_VideoController | %{ \"$($_.Name)|$($_.CurrentHorizontalResolution)x$($_.CurrentVerticalResolution)|$($_.CurrentRefreshRate)\" }")
    rows = [l.split("|") for l in out.splitlines() if l.count("|") == 2 and "x" in l.split("|")[1] and l.split("|")[1] != "x"]
    try:
        import ctypes
        n = ctypes.windll.user32.GetSystemMetrics(80)
    except Exception:
        n = None
    return rows, n


def wifi():
    """Connection type + network name (no location permission needed)."""
    out = _ps("Get-NetConnectionProfile | %{ \"$($_.InterfaceAlias)|$($_.Name)|$($_.IPv4Connectivity)\" }")
    rows = [l.split("|") for l in out.splitlines() if l.count("|") == 2]
    if not rows:
        return {"state": "disconnected", "ssid": "", "signal": "", "via": ""}
    wl = [r for r in rows if re.search(r"wi-?fi|wireless|wlan", r[0], re.I)]
    r = (wl or rows)[0]
    return {"state": "connected" if r[2] in ("Internet", "LocalNetwork") else r[2], "ssid": r[1], "signal": "", "via": "Wi-Fi" if wl else r[0]}


def bluetooth():
    out = _ps("(Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | ?{$_.FriendlyName -match 'Radio|Adapter|Wireless Bluetooth|Generic Bluetooth' } | select -First 1).Status")
    return out or None


def power_plan():
    out = _run(["powercfg", "/getactivescheme"])
    m = re.search(r"\((.+)\)", out)
    return m.group(1) if m else None


def power_plans():
    out = _run(["powercfg", "/list"])
    return [(g, n) for g, n in re.findall(r"GUID:\s*([0-9a-f-]{36})\s*\((.+?)\)", out, re.I)]


def report(what="all"):
    parts = []
    w = what.lower()
    if w in ("all", "volume", "sound", "audio"):
        v, mute = volume()
        if v is not None:
            parts.append(f"Volume is {v} percent" + (", muted" if mute else "") + ".")
        dev = default_output()
        if dev:
            parts.append(f"The Windows default output is {dev}.")
    if w in ("all", "display", "screen", "resolution"):
        rows, n = display()
        if rows:
            parts.append("Display: " + "; ".join(f"{r[1]} at {r[2]} hertz" for r in rows[:2]) + (f", {n} monitors." if n else "."))
    if w in ("all", "wifi", "network", "internet"):
        wf = wifi()
        if wf["state"] != "connected":
            parts.append("You don't seem to be connected to a network.")
        elif wf["via"] == "Wi-Fi":
            parts.append(f"You're on Wi-Fi, network {wf['ssid']}.")
        else:
            parts.append(f"You're online through {wf['via']} (network {wf['ssid']}), not Wi-Fi.")
    if w in ("all", "bluetooth"):
        b = bluetooth()
        parts.append(f"Bluetooth radio status: {b}." if b else "I couldn't find a Bluetooth radio.")
    if w in ("all", "power", "power plan"):
        p = power_plan()
        if p:
            parts.append(f"Power plan is {p}.")
    return " ".join(parts) or "I couldn't read those settings just now."


def set_power_plan(name):
    """Change power plan: asks first (confirm system)."""
    from .pc import ask
    plans = power_plans()
    from .resolve import score
    best = max(plans, key=lambda p: score(name, p[1]), default=None)
    if not best or score(name, best[1]) < 0.6:
        return "I couldn't find that power plan. You have: " + ", ".join(p[1] for p in plans) + "."
    guid, label = best
    return ask(f"Switch the power plan to {label}? Say yes to confirm.", f"set power plan to {label}",
               lambda: (_run(["powercfg", "/setactive", guid]), f"Power plan set to {label}.")[1])
