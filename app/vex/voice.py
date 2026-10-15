"""Vex 3.7.1 humanlike speech: clean text for the ear, conversational phrasing, and a per-sentence prosody plan
(rate/pitch variation + natural pauses). edge-tts 7 no longer accepts custom SSML, so prosody is applied per chunk
through its rate/pitch/volume parameters and pauses are real silence between chunks. No voice cloning."""
import re, random

CONTRACT = [(r"\bI am\b", "I'm"), (r"\bI will\b", "I'll"), (r"\bI would\b", "I'd"), (r"\bI have (?=(?:been|done|got|just|already|found|set|added|opened|closed|made|started|stopped|put|sent|saved|no)\b)", "I've "),
            (r"\byou are\b", "you're"), (r"\bYou are\b", "You're"), (r"\bwe are\b", "we're"), (r"\bthey are\b", "they're"), (r"\bthat is\b", "that's"), (r"\bThat is\b", "That's"),
            (r"\bit is\b", "it's"), (r"\bIt is\b", "It's"), (r"\bthere is\b", "there's"), (r"\bThere is\b", "There's"), (r"\bwhat is\b", "what's"), (r"\bWhat is\b", "What's"),
            (r"\bdo not\b", "don't"), (r"\bDo not\b", "Don't"), (r"\bdoes not\b", "doesn't"), (r"\bdid not\b", "didn't"), (r"\bcannot\b", "can't"), (r"\bCannot\b", "Can't"),
            (r"\bwill not\b", "won't"), (r"\bis not\b", "isn't"), (r"\bare not\b", "aren't"), (r"\bwas not\b", "wasn't"), (r"\bhave not\b", "haven't"), (r"\bshould not\b", "shouldn't"),
            (r"\bwould not\b", "wouldn't"), (r"\bcould not\b", "couldn't"), (r"\blet us\b", "let's"), (r"\bLet us\b", "Let's"), (r"\byou will\b", "you'll"), (r"\bYou will\b", "You'll"),
            (r"\bhere is\b", "here's"), (r"\bHere is\b", "Here's")]
WARM = [(r"^Certainly\.\s*", "Of course. "), (r"\bPlease be advised that\s*", ""), (r"\bI apologi[sz]e for the inconvenience\b", "Sorry about that"),
        (r"\bUnfortunately, I am unable to\b", "I'm afraid I can't"), (r"\bI am unable to\b", "I can't"), (r"\bI'm unable to\b", "I can't"), (r"\bIn order to\b", "To"), (r"\bin order to\b", "to"),
        (r";\s*however,\s*", ". Mind you, "), (r",\s*however,\s*", ", though, "), (r"\bAdditionally,\s*", "Also, "), (r"\bHowever,\s*", "Mind you, "), (r"\bTherefore,\s*", "So, "), (r"\butili[sz]e\b", "use"), (r"\bcommence\b", "start")]
SYM = [("&", " and "), ("%", " percent"), ("°C", " degrees"), ("°F", " degrees"), ("°", " degrees"), ("+", " plus "), ("=", " equals "), ("@", " at "), ("~", "about "), ("→", " to "), ("->", " to "),
       ("×", " times "), ("€", " euros"), ("£", " pounds"), ("…", "."), ("—", ", "), ("–", ", "), (" - ", ", ")]


def clean(text):
    """Make text safe and natural to say: no markdown, URLs, code, emoji or stray symbols."""
    t = text or ""
    t = re.sub(r"```.*?```", " I've put the code on screen. ", t, flags=re.S)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)                       # [label](url) -> label
    t = re.sub(r"(?i)\b(?:https?://|www\.)\S+", lambda m: _site(m.group(0)), t)
    t = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", "that email address", t)
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", t)                           # headings
    t = re.sub(r"(?m)^\s*(?:[-*•▪◦]|\d+[.)])\s+", "", t)                    # bullets / numbered lists
    t = re.sub(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1", r"\2", t)            # bold/italic
    t = re.sub(r"\|", ", ", t)
    t = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]", "", t)  # emoji
    # dollars before symbol table so "$5" -> "5 dollars"
    t = re.sub(r"\$(\d[\d,.]*)", r"\1 dollars", t)
    for a, b in SYM:
        t = t.replace(a, b)
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)                            # 10,000 -> 10000 (read as a number)
    t = re.sub(r"(?<=\w)/(?=\w)", " or ", t)
    t = re.sub(r"[*#_^<>{}\[\]\\|$`]", " ", t)
    t = re.sub(r"\s*\n\s*\n\s*", ". ", t); t = re.sub(r"\s*\n\s*", ", ", t)
    t = re.sub(r"\s+([,.!?;:])", r"\1", t); t = re.sub(r"([,;:])(?=\S)", r"\1 ", t)
    t = re.sub(r"([.!?])\1+", r"\1", t); t = re.sub(r"[,;:]\s*([.!?])", r"\1", t)
    t = re.sub(r"\(\s*([^)]*?)\s*\)", r", \1,", t); t = re.sub(r",\s*,", ",", t)
    return re.sub(r"\s+", " ", t).strip(" ,")


def _site(u):
    m = re.match(r"(?i)(?:https?://)?(?:www\.)?([\w-]+)\.(?:com|org|net|tv|gg|io|co|uk|dev)", u)
    return f"the {m.group(1).title()} link" if m else "the link on screen"


ABBR = [(r"\be\.g\.", "for example"), (r"\bi\.e\.", "that is"), (r"\betc\.", "and so on"), (r"\bvs\.?", "versus"), (r"(?<=\d) ?min\b", " minutes"),
        (r"(?<=\d) ?secs?\b", " seconds"), (r"(?<=\d) ?hrs?\b", " hours"), (r"(?<=\d) ?ms\b", " milliseconds"), (r"(?<=\d) ?GB\b", " gigabytes"), (r"(?<=\d) ?MB\b", " megabytes"),
        (r"(?<=\d) ?fps\b", " F P S"), (r"\bw/\s?", "with "), (r"\bapprox\.", "about")]


def converse(text):
    t = text
    for a, b in ABBR: t = re.sub(a, b, t, flags=re.I if "e\\.g" in a else 0)
    for a, b in WARM: t = re.sub(a, b, t)
    for a, b in CONTRACT: t = re.sub(a, b, t)
    return t


def sentences(text):
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text) if p.strip()]
    out = []
    for p in parts:   # long sentences break at a natural comma/semicolon near the middle
        while len(p) > 170:
            cut = [m.end() for m in re.finditer(r"[,;:]\s", p) if 50 < m.end() < len(p) - 30]
            if not cut: break
            c = min(cut, key=lambda x: abs(x - len(p) / 2))
            out.append((p[:c].strip().rstrip(",;:"), "clause")); p = p[c:].strip()
        out.append((p, "sentence"))
    return out


def _pct(s): return int(re.sub(r"[^-\d]", "", s or "0") or 0)
def _hz(s): return int(re.sub(r"[^-\d]", "", s or "0") or 0)


HAPPY = re.compile(r"(?i)\b(great|brilliant|excellent|nice|done|complete|completed|finished|nominal|all good|well played|congrat\w*|success\w*|ready|online|fantastic|good news|perfect|lovely|record)\b")
SOFT = re.compile(r"(?i)\b(warning|careful|heads up|high|hot|full|low|failed|error|can't|cannot|couldn't|afraid|sorry|unfortunately|problem|issue|crash\w*|blocked|offline|danger|late|tired|goodnight)\b")
NOFILL = re.compile(r"(?i)^(all systems|very good|initiating|good (morning|afternoon|evening|night)|goodnight|done|yes|no\b|of course|shall i|sure|okay|ok\b|right|hmm|ah|focus|combat|study|creator|business|chill|stealth|diagnostics|default|back to|sound effects|speaking|taking it|undone|look reset|goal|recording checklist|modes:|scan complete|running a full)")


def emotion(s):
    h, w = len(HAPPY.findall(s)), len(SOFT.findall(s))
    return "soft" if w > h else ("happy" if h > w else "neutral")


def filler(t, rnd):
    """Occasionally start like a person would: 'Right,' 'Hmm,' 'Ah,'. Never on confirmations, mode lines or boot."""
    if len(t) < 60 or NOFILL.match(t) or rnd.random() > 0.3:
        return t
    if re.search(r"(?i)\b(think|maybe|perhaps|probably|might|depends|not sure|guess)\b", t): f = "Hmm,"
    elif re.search(r"(?i)\b(found|there it is|looks like|got it|here's|turns out)\b", t): f = "Ah,"
    else: f = rnd.choice(["Right,", "Right then,", "Well,"])
    return f + " " + t[0].lower() + t[1:] if not t.startswith("I ") and not t.startswith("I'") else f + " " + t


def plan(text, base_rate="-1%", base_pitch="-4Hz", seed=None):
    """-> list of (chunk, rate, pitch, pause_ms_after). Pitch varies sentence to sentence; questions lift,
    the last line settles; short lines are a touch more deliberate; pauses breathe a little (jittered)."""
    rnd = random.Random(seed if seed is not None else __import__("zlib").crc32(text.encode()) & 0xffff)
    t = filler(converse(clean(text)), rnd)
    segs = sentences(t)
    mood = emotion(t)
    r0, p0 = _pct(base_rate), _hz(base_pitch)
    walk = [0, -3, 2, -1, 3, -2]
    out = []
    for i, (s, kind) in enumerate(segs):
        words = len(s.split())
        r, p = r0, p0 + walk[i % len(walk)] + rnd.choice((-1, 0, 1))
        if s.endswith("?"): p += 4; r += 1
        elif s.endswith("!"): p += 3; r += 3
        if words <= 4: r -= 4                       # "Very good, sir." lands calmly
        elif words >= 18: r += 3                    # long lines flow a bit quicker
        last = i == len(segs) - 1
        if last and len(segs) > 1 and not s.endswith("?"): p -= 2; r -= 1
        em = emotion(s) if emotion(s) != "neutral" else mood
        vol = "+0%"
        if em == "happy": r += 4; p += 3                      # brighter, a little quicker for good news
        elif em == "soft": r -= 4; p -= 3; vol = "-12%"       # gentler and quieter for warnings
        p = max(p0 - 6, min(p0 + 8, p))
        if kind == "clause": pause = rnd.randint(120, 170)
        elif last: pause = 0
        else: pause = rnd.randint(250, 340) + (60 if s.endswith("?") else 0)
        out.append((s, f"{r:+d}%", f"{p:+d}Hz", pause, vol))
    return out
