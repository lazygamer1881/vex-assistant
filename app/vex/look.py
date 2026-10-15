"""Vex 3.2 self-customization. Vex can change ONLY these whitelisted look/behaviour values (no code changes, ever)."""
import re, time, copy
from . import config

DEFAULT = {"hue": 0, "sat": 1.0, "dark": 0.0, "text": 1.0, "orb": 1.0, "glow": 1.0, "scan": 1.0, "preset": "Arc Blue"}
LIMITS = {"hue": (-180, 180), "sat": (0.0, 1.6), "dark": (0.0, 0.55), "text": (0.8, 1.6), "orb": (0.6, 1.5), "glow": (0.3, 1.6), "scan": (0.0, 2.0)}
BASE_HUE = 190  # the dashboard is drawn in cyan; colours are a hue shift from it
COLORS = {"red": 355, "crimson": 350, "orange": 25, "gold": 45, "yellow": 52, "lime": 95, "green": 140, "emerald": 150, "teal": 172,
          "cyan": 190, "blue": 212, "navy": 225, "purple": 272, "violet": 265, "magenta": 305, "pink": 325, "rose": 340, "amber": 38, "aqua": 180, "indigo": 240, "lavender": 260, "white": 190, "silver": 200}
PRESETS = {
    "arc blue": {"hue": 0, "sat": 1.0, "dark": 0.0, "glow": 1.0},
    "crimson": {"hue": 165, "sat": 1.1, "dark": 0.1, "glow": 0.9},
    "stealth": {"hue": 20, "sat": 0.15, "dark": 0.35, "glow": 0.55, "scan": 0.6},
    "gold": {"hue": -145, "sat": 1.05, "dark": 0.05, "glow": 0.9},
    "emerald": {"hue": -45, "sat": 1.0, "dark": 0.05},
    "nebula": {"hue": 80, "sat": 1.15, "dark": 0.05, "glow": 1.1},
}
SEQ = {"n": 0}
_hist = []


def current():
    d = copy.deepcopy(DEFAULT); d.update({k: v for k, v in (config.get("look") or {}).items() if k in DEFAULT}); return d


def _clamp(d):
    for k, (lo, hi) in LIMITS.items():
        d[k] = max(lo, min(hi, float(d[k])))
    d["hue"] = round(d["hue"])
    return d


def apply(changes, label):
    before = current()
    after = _clamp({**before, **changes})
    _hist.append((before, label, time.time())); del _hist[:-20]
    config.save({"look": after}); SEQ["n"] += 1
    return after


def _hue_for(color):
    h = (COLORS[color] - BASE_HUE + 540) % 360 - 180
    return h


def protocol_look(color):
    """Theme for '<color> protocol'. Returns (look changes, css colour) or None."""
    c = color.lower().strip()
    if c in ("stealth", "black", "dark", "night"):
        return {**PRESETS["stealth"], "preset": "Stealth"}, "#9fb3c2"
    if c in ("white", "silver", "ghost", "snow"):
        return {"hue": 0, "sat": 0.08, "dark": 0.0, "glow": 1.1, "preset": c.title()}, "#eef6ff"
    if c in PRESETS:
        h = (BASE_HUE + PRESETS[c].get("hue", 0)) % 360
        return {**PRESETS[c], "preset": c.title()}, f"hsl({h},100%,62%)"
    if c in COLORS:
        return {"hue": _hue_for(c), "sat": 1.15, "preset": c.title()}, f"hsl({COLORS[c]},100%,62%)"
    return None


def undo():
    if not _hist:
        return "Nothing to undo."
    before, label, _ = _hist.pop()
    if "__name" in before:
        config.save({"assistant_name": before["__name"]}); return f"Undone: I'm {before['__name']} again."
    config.save({"look": before}); SEQ["n"] += 1
    return f"Undone: {label}."


def handle(t):
    """t = normalised text. Returns spoken reply or None if it isn't a look command."""
    if re.fullmatch(r"(?:undo that|undo|revert that|put it back|change it back)", t):
        return undo() if _hist else None
    if re.fullmatch(r"reset (?:your |the )?(?:look|theme|style|colou?rs?|appearance)", t):
        apply(dict(DEFAULT), "reset look"); return "Look reset to Arc Blue."
    m = re.search(r"\b(?:theme|preset|mode|look|style)\b.*?\b(arc blue|crimson|stealth|gold|emerald|nebula)\b|\b(?:switch|change|go|set) (?:to |into )?(arc blue|crimson|stealth|gold|emerald|nebula)(?: mode| theme)?\b|^(arc blue|crimson|stealth|gold|emerald|nebula) (?:mode|theme)$", t)
    if m:
        name = next(g for g in m.groups() if g)
        apply({**PRESETS[name], "preset": name.title()}, name.title() + " theme"); return f"{name.title()} theme engaged."
    m = re.search(r"\b(?:make|turn|change|set|paint)\b.*?\b(?:orb|you|yourself|theme|colou?rs?|accent|dashboard|it|everything|hud)\b.*?\b(" + "|".join(COLORS) + r")\b", t) \
        or re.fullmatch(r"(?:go )?(" + "|".join(COLORS) + r")(?: please)?", t)
    if m:
        c = m.group(1); apply({"hue": _hue_for(c), "preset": "Custom"}, c + " colour"); return f"Going {c}."
    m = re.search(r"\b(?:make )?(?:it |yourself |the dashboard |everything )?(darker|lighter|brighter|dimmer)\b", t)
    if m and re.search(r"^(?:make|go|be|a bit|little|bit|darker|lighter|brighter|dimmer|turn)", t):
        w = m.group(1); d = current()
        if w in ("darker", "dimmer"): apply({"dark": d["dark"] + 0.12, "glow": d["glow"] - 0.12}, "darker")
        else: apply({"dark": d["dark"] - 0.12, "glow": d["glow"] + 0.12}, "brighter")
        return "Done." if w != "brighter" else "Brightening up."
    m = re.search(r"\b(bigger|larger|smaller)\s+(text|font|words|writing|orb|core)\b|\b(?:make )?(?:the )?(text|font|orb|core)\s+(bigger|larger|smaller)\b", t)
    if m:
        size = m.group(1) or m.group(4); what = m.group(2) or m.group(3)
        k = "orb" if what in ("orb", "core") else "text"; d = current()
        apply({k: d[k] + (0.12 if size != "smaller" else -0.12)}, f"{size} {what}"); return "Adjusted."
    m = re.search(r"\b(more|less|no|fewer)\s+(scan ?lines|glow)\b", t)
    if m:
        k = "scan" if "scan" in m.group(2) else "glow"; d = current()
        apply({k: 0 if m.group(1) == "no" else d[k] + (0.3 if m.group(1) == "more" else -0.3)}, f"{m.group(1)} {m.group(2)}"); return "Done."
    m = re.fullmatch(r"(?:change|set) your name to ([a-z][a-z0-9 \-]{0,18})|(?:call yourself|your name is now|i'?ll call you) ([a-z][a-z0-9 \-]{0,18})", t)
    if m:
        n = (m.group(1) or m.group(2)).strip().title()
        old = config.get("assistant_name"); config.save({"assistant_name": n})
        _hist.append(({"__name": old}, "name change", time.time()))
        return f"Very well. I'm {n} now. The wake phrases still work; say 'hey {n.lower()}' after you add it in Settings."
    m = re.search(r"\b(faster|slower|quicker)\b.*\b(voice|speech|talking|speaking|talk|speak)\b|\b(?:talk|speak)\s+(faster|slower|quicker)\b", t)
    if m:
        w = m.group(1) or m.group(3)
        def bump(v, step):
            try: n = int(str(v).replace("%", ""))
            except Exception: n = 0
            n = max(-40, min(40, n + step)); return f"{n:+d}%"
        step = -8 if w == "slower" else 8
        config.save({"voice_rate": bump(config.get("voice_rate") or "-1%", step), "butler_rate": bump(config.get("butler_rate"), step), "edge_rate": bump(config.get("edge_rate"), step)})
        return "Speaking faster." if step > 0 else "Taking it slower."
    return None
