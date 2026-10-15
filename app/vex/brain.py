"""Turns what the user said into actions + a short casual reply.

Fast path: a rule parser handles the common commands instantly and reliably.
Anything else goes to the local LLM (Ollama) with tool calling.
"""
import re, json, time, random, datetime, logging, urllib.request, threading

from . import config, tools, pc, actlog

log = logging.getLogger("vex.brain")

VERB_OPEN = r"(?:open|launch|start|pull up|bring up|run|boot up|boot|fire up|load|load up|put on|play|go to)"
VERB_CLOSE = r"(?:close|quit|exit|kill)"
FILLER = r"^(?:(?:yo|hey|ok|okay|alright|aight|bro|dude|um|uh|so|and|now|please|can you|could you|would you|will you|i need you to|i want you to|go ahead and|just)\s+)+"

SLEEP_WORDS = {"go to sleep", "that's all", "thats all", "stop listening", "bye", "peace", "nevermind that's it",
               "that's it", "go sleep", "sleep", "dismissed", "later", "see ya", "see you"}
YES = {"yes", "yeah", "yep", "yup", "sure", "do it", "pull it up", "bet", "ok", "okay", "please", "go ahead", "open it", "yes please", "yeah pull it up", "sure thing"}
NO = {"no", "nah", "nope", "no thanks", "not now", "skip"}
SEND = {"send", "send it", "post it", "send that", "yeah send it", "yes send it", "send the message", "hit send", "post"}
CONFIRM_YES = {"yes", "yeah", "yep", "yup", "yes do it", "yeah do it", "do it", "confirm", "yes please", "go ahead", "yes go ahead",
               "yeah go ahead", "yes sir", "yes i'm sure", "i'm sure", "yes confirm", "affirmative", "yeah i'm sure",
               "send", "send it", "post it", "yes send it", "yeah send it", "hit send"}
KILL = {"stop", "stop stop", "stop it", "stop that", "stop everything", "cancel everything", "abort", "freeze", "hold up stop", "vex stop"}
CANCEL = {"cancel", "don't send", "dont send", "don't send it", "never mind", "nevermind", "cancel that", "scrap that", "no don't send it"}


def norm(text):
    t = text.lower().strip()
    t = t.replace("’", "'")
    t = re.sub(r"[^\w\s':,.\-\\/]", " ", t)
    t = re.sub(r"(?<!\w)[.\-]|[.\-](?!\w)", " ", t)  # keep dots/dashes only inside words (clip.mp4, projects)
    t = re.sub(r"\s+", " ", t).strip(" ,.")
    name = re.escape(config.get("assistant_name").lower())
    t = re.sub(rf"^(?:hey |yo |ok |okay )?{name}[, ]*", "", t)
    for p in config.get("wake_phrases") or []:
        p = p.lower().strip()
        if p and t.startswith(p):
            t = t[len(p):].strip(" ,")
    t = re.sub(FILLER, "", t).strip(" ,")
    return t


def winutil_combo_ok(text):
    from . import winutil
    return winutil.parse_combo(text) is not None


def caps(msg):
    msg = msg.strip().strip("\"'")
    msg = re.sub(r"\bi\b", "I", msg)
    msg = re.sub(r"\bim\b", "I'm", msg)
    return msg[:1].upper() + msg[1:] if len(msg.split()) > 2 else msg


class Brain:
    def __init__(self):
        self.keep_alive = "15m"   # core sets -1 (forever) when the GPU has room and no game is running
        self.cpu_only = False     # True while Gorilla Tag / SteamVR run: model runs in RAM, GPU stays free
        self.history = []
        self.pending_confirm = None  # {"fn", "desc", "at"} - a risky action waiting for "yes"
        self.pending_yes = None  # callable for "yeah" answers (e.g. open the trending game)

    # ------------------------------------------------------------ public
    def handle(self, text):
        """Returns dict(say=str, after=callable|None, sleep=bool)."""
        raw = (text or "").strip()
        self._raw = raw
        t = norm(raw)
        if not t:
            return {"say": "", "sleep": False}
        try:  # remember the last app/game mentioned so "bring it up" / "open that" work
            from . import resolve as _rs
            m = re.search(r"\b(?:about|is|play|playing|like|open|launch|bring up|pull up|show me)\s+(?:the |my )?([a-z0-9][\w .'-]{1,30}?)(?:\?|$|,| (?:is|was|today|later|tonight))", t)
            if m:
                k, info = tools.resolve_app(m.group(1))
                if info:
                    _rs.note(info["label"], "app")
        except Exception:
            pass
        res = self._special(t)
        if res is None:
            res = self._rules(t)
        if res is None:
            res = self._llm(raw)
        if isinstance(res, str):
            res = {"say": res}
        res.setdefault("sleep", False)
        if res.get("confirm"):
            self.pending_confirm = {"fn": res["confirm"], "desc": res.get("confirm_desc", ""), "at": time.time()}
        self._remember(raw, res.get("say", ""))
        return res

    # ------------------------------------------------------------ Vex 4.2: help card, quick timers/reminders, memory recall
    def _v42(self, b):
        from . import assist as _as
        b = re.sub(r"^(?:hey |yo |ok |okay )?(?:vex[, ]+)?(?:can you |could you |please )?", "", b).strip()
        b = re.sub(r" please$", "", b)
        if re.fullmatch(r"(?:so )?(?:what can you do|what (?:all )?can you help (?:me )?with|what are your (?:commands|features|abilities|skills)|what (?:commands|things) can i (?:say|ask)|what do you do|help|help me out|show (?:me )?(?:the )?(?:help|commands)(?: card)?|how do i use you)", b):
            try:
                from . import product
                product.emit("help42", {"on": True})
            except Exception:
                log.exception("help card")
            return {"say": "Here's what I can do. Apps, timers, reminders, memory, the show-me panel, PC control and questions. Just ask."}
        if re.fullmatch(r"(?:close|hide|dismiss) (?:the )?(?:help|commands)(?: card)?|got it", b):
            try:
                from . import product
                product.emit("help42", {"on": False})
            except Exception: pass
            return {"say": "Closed."} if b != "got it" else None
        # 4.2 dashboard tabs by voice: "show system tab", "go to the activity tab", "open memory tab"
        m = re.fullmatch(r"(?:show|open|go to|switch to|bring up|take me to)(?: me)? (?:the |my )?(home|system|activity|memory|memories)(?: tab| page| screen| view)"
                         r"|(?:show|open|switch to)(?: me)? (?:the )?(system|activity)(?: stats| info)?|(home|system|activity|memory) tab", b)
        if m:
            tab = (m.group(1) or m.group(2) or m.group(3)).replace("memories", "memory")
            if tab == "memory" and b.endswith(" page"):
                tab = None                      # "open memory page" keeps opening the full Memory page
        if m and tab:
            try:
                from . import product
                config.set_view("full"); product.emit("tab42", {"tab": tab})
            except Exception:
                log.exception("tab42")
            return {"say": {"home": "Home.", "system": "System tab.", "activity": "Here's the activity.", "memory": "Here's what I remember."}[tab]}
        # timers (focus / pomodoro timers belong to the modes system)
        if re.search(r"\b(?:focus|study|pomodoro)\b", b):
            return None
        m = re.fullmatch(r"(?:set|start|make|put on|give me)?\s*(?:a |an |my )?timer (?:for |of )?(.+?)(?: (?:for|called|named|labell?ed) (?:the |my )?(.+))?", b) \
            or re.fullmatch(r"(?:set|start|make|put on|give me)?\s*(?:a |an )?((?:[\w.]+[ -]){1,4}?)(?:minute|min|second|sec|hour)s?(?: long)? (?:(.+?) )?timer", b)
        if m:
            g1, g2 = m.group(1), m.group(2)
            if "timer (" not in m.re.pattern:  # second form: number + unit
                unit = re.search(r"(minute|min|second|sec|hour)", b).group(1)
                g1 = g1.strip(" -") + " " + {"min": "minute", "sec": "second"}.get(unit, unit) + "s"
            r = _as.set_timer(g1, g2 or "")
            if r:
                return r
        if re.fullmatch(r"(?:how (?:much time|long)(?: is)?(?: left| remaining)?(?: (?:on|for) (?:the |my )?(?:\w+ )?timers?)?|(?:check|what'?s|whats) (?:on )?(?:the |my )?timers?|time left(?: on (?:the |my )?(?:\w+ )?timer)?|how long (?:until|till|til) (?:the |my )?(?:\w+ )?timer(?: (?:is )?(?:up|done|goes off))?)", b) and "timer" in b or re.fullmatch(r"how much time is left", b):
            lm = re.search(r"(?:on|for) (?:the |my )?(\w+) timer", b)
            return _as.timers_left(lm.group(1) if lm else "")
        m = re.fullmatch(r"(?:cancel|stop|clear|kill|end|delete) (?:the |my |all (?:the |my )?)?(?:(\w+) )?timers?", b)
        if m:
            return _as.cancel_timers("all" if b.find("all") >= 0 else (m.group(1) or ""))
        # reminders (fast path, no LLM round trip)
        m = re.fullmatch(r"remind me (?:to |about )?(.+?) (in .+|at .+|tomorrow(?: at)? .+|tonight at .+)", b)
        m2 = re.fullmatch(r"remind me (in .+?|at .+?|tomorrow(?: at)? [\w: .]+?|tonight at [\w: .]+?) (?:to|about|that) (.+)", b)
        if m2 or m:
            what, when = (m2.group(2), m2.group(1)) if m2 else (m.group(1), m.group(2))
            when = re.sub(r"^tonight at ", "", when)
            if _as._parse_when(when):
                return _as.set_reminder(what, when)
        if re.fullmatch(r"(?:what (?:are|is) )?(?:my |the )?(?:reminders?|timers and reminders)|what reminders do i have|do i have any reminders|list (?:my )?reminders|any reminders", b):
            t = _as.timers_left() if any(x["kind"] == "timer" for x in _as.active_timers()) else ""
            l = _as.list_reminders()
            return (t + " " + l).strip() if t and l != "No reminders set." else (t or l)
        # memory recall
        m = re.fullmatch(r"what do you (?:remember|know) about (me|myself)|what do you remember(?: about (.+))?|do you remember (?:what |when |where |who )?(?:my |about )?(.+)|what(?:'s| is) my (.+?)(?: again)?", b)
        if m:
            topic = m.group(2) or m.group(3) or m.group(4) or ""
            if m.group(4):
                want = _as._toks(m.group(4))
                r = [x for x in _as.relevant_memories("my " + m.group(4), 4) if want and want <= _as._toks(x)][:2]
                return ("You told me: " + "; ".join(r) + ".") if r else None
            return _as.recall_about(topic)
        return None

    # ------------------------------------------------------------ Vex 3.2: look, agents, accounts, displays
    def _do_scan(self):
        from . import diagnostics
        d = diagnostics.scan()
        try:
            emit = getattr(self, "emit_cb", None)
            emit and emit("scan", d)
            from . import displays; displays.show_temp(20, "SYSTEM SCAN // " + d["at"], d["say"])
        except Exception: log.exception("scan emit")
        return d["say"]

    def _v32(self, base, t):
        from . import look, connections, accounts, displays
        from . import product
        r42 = self._v42(base.strip(" ,.!?"))
        if r42 is not None:
            return r42 if isinstance(r42, dict) else {"say": r42}
        r40 = product.command(base, t)
        if r40: return r40
        m = re.fullmatch(r"(?:open|show)(?: me)? (?:the )?(connections|connection|agents|accounts|settings|chat|memory)(?: tab| page)?", base)
        if m:
            p = {"connection": "connections", "agents": "connections", "accounts": "connections"}.get(m.group(1), m.group(1))
            config.set_view("full"); config.VIEW["page"] = p; return {"say": "Here you go."}
        m = re.match(r"(?:ask|use) (chatgpt|gpt|open ai|openai|claude|anthropic|gemini|groq|grok|open router|openrouter|lm studio|ollama|local|my agent|custom agent|webhook|agent)[,:]? (?:to |about |whether |if )?(.+)", base)
        if m:
            who = connections.resolve_alias(m.group(1)); q = (self._raw or m.group(2))
            q = re.sub(r"(?i)^.*?\b(?:" + re.escape(m.group(1)) + r")\b[,:]?\s*(?:to |about )?", "", q, count=1) or m.group(2)
            if not connections.configured(who):
                return {"say": f"{connections.AGENTS[who][0]} isn't connected yet. Paste a key in the Connections tab, it's optional."}
            try:
                if who == "webhook":
                    ans = connections.ask_webhook(q)
                else:
                    ans = self.engine.ask(q, self.history[-10:], "voice", brain=who).get("say", "")
            except Exception as e:
                return {"say": f"{connections.AGENTS[who][0]} didn't answer: {str(e)[:80]}"}
            return {"say": " ".join(re.split(r"(?<=[.!?])\s+", ans)[:3]), "detail": f"[{connections.AGENTS[who][0]}] {ans}"}
        if re.fullmatch(r"(?:please |vex |hey vex )?(?:run (?:a |the )?(?:full |system |complete |quick )?(?:scan|diagnostics?|system check|systems check)|(?:full |system )?diagnostics|scan (?:my |the )?(?:pc|computer|system)|system scan|how'?s my pc (?:doing|running))(?: please)?", base):
            return {"say": "Running a full diagnostic, sir. " + self._do_scan()}
        from . import modes
        _say = getattr(self, "say_cb", None) or (lambda t: None)
        def _note(title, text):
            e = getattr(self, "emit_cb", None)
            e and e("notify", {"title": title, "text": text})
        r = modes.handle(base, _say, _note)
        if r: return {"say": r}
        m = re.fullmatch(r"(?:(?:turn |switch )?(on|off|enable|disable|mute|unmute) (?:the )?(?:ui |interface )?(?:sound effects|sounds|sfx|blips|beeps))|(?:sound effects|sfx) (on|off)", base)
        if m:
            g = (m.group(1) or m.group(2)); on = g in ("on", "enable", "unmute")
            config.save({"ui_sounds": on}); return {"say": "Sound effects on." if on else "Sound effects off."}
        m = re.fullmatch(r"(?:(?:hey |yo |ok )?\w+[, ]+)?(?:go |switch to |engage |activate |initiate |enable |start )?(?:the )?([a-z]+)(?: mode| protocol)(?: please| now)?", base)
        if m and (modes.key(m.group(1)) or look.protocol_look(m.group(1))):
            c = m.group(1); from . import protocol
            fn = getattr(self, "say_cb", None) or (lambda t: None)
            mk = modes.key(c)
            if mk:
                col = {"black": "stealth"}.get(mk, mk)
                def done(_mk=mk):
                    modes.set_mode(_mk)
                    if _mk == "white":
                        fn("Diagnostics mode. " + self._do_scan())
                    else:
                        fn(modes.MODES[_mk]["line"])
                if mk == "blue":
                    look.apply(dict(look.DEFAULT), "blue mode")
                    modes.set_mode("blue")
                    return {"say": "Back to default assistant mode. Standing by, sir."}
                return {"say": f"Very good, sir. Initiating {c} protocol.", "after": lambda: threading.Thread(target=protocol.run, args=(col, fn, done), daemon=True).start()}
            return {"say": f"Very good, sir. Initiating {c} protocol.", "after": lambda: threading.Thread(target=protocol.run, args=(c, fn), daemon=True).start()}
        try:
            r = look.handle(base)
            if r:
                if r.startswith("Look reset"): modes.set_mode("blue"); r += " Default assistant mode."
                return {"say": r}
        except Exception:
            log.exception("look")
        try:
            if re.search(r"\b(what'?s|what is) (playing|this song)\b.*spotify|\bspotify\b.*\b(playing|song)\b", base) and accounts.vault.get("oauth_spotify"):
                return {"say": accounts.spotify_now()}
            if re.search(r"\b(my calendar|my schedule|next meeting|what'?s next on my calendar|calendar today)\b", base) and accounts.vault.get("oauth_google"):
                return {"say": accounts.calendar_next()}
            if re.search(r"\b(unread (emails?|mail)|new emails?|check my (email|gmail|inbox))\b", base) and accounts.vault.get("oauth_google"):
                return {"say": accounts.gmail_unread()}
            if re.search(r"\b(channel stats|my (youtube )?(subs|subscribers|channel stats|views))\b", base) and accounts.vault.get("oauth_youtube"):
                return {"say": accounts.youtube_stats()}
        except Exception as e:
            return {"say": "That account didn't answer: " + str(e)[:90]}
        m = re.match(r"(?:post|send) (?:this |a message )?(?:to|on|in) (?:the )?discord(?: webhook| channel)?[,:]? (?:saying |that )?(.+)", base)
        if m and config.get("discord_webhook_url"):
            msg = re.sub(r"(?i)^.*?discord(?: webhook| channel)?[,:]?\s*(?:saying |that )?", "", self._raw or "", count=1) or m.group(2)
            return {"say": f"I'll post to your Discord channel: \"{msg[:120]}\". Shall I proceed?", "confirm": lambda: accounts.discord_post(msg), "confirm_desc": "discord webhook post: " + msg[:80]}
        m = re.fullmatch(r"(?:move|put|send) (?:yourself |vex |the orb |it |the ai )?(?:to|on|onto) (?:the )?(?:monitor|screen|display) (one|two|three|1|2|3)|(?:move|put) (?:yourself |vex |it )?(?:to|on) (?:the )?(left|right|main|second|other) (?:monitor|screen|display)", base)
        if m:
            w = m.group(1) or m.group(2)
            n = {"one": 1, "two": 2, "three": 3, "1": 1, "2": 2, "3": 3, "left": 1, "main": 1, "right": 2, "second": 2}.get(w)
            if w == "other": n = 1 if (config.get("main_monitor") or 2) == 2 else 2
            return {"say": displays.move_to(n)}
        if re.fullmatch(r"(?:span|use|stretch across|extend (?:to|across)) (?:all|both|every) (?:the )?(?:monitors|screens|displays)|span(?: (?:monitors|screens))?|multi ?monitor(?: mode)?|dual (?:monitor|screen)(?: mode)?|show (?:me )?(?:the )?(?:stats|hud|system stats|dashboard|info) (?:on|to) (?:the )?(?:other|second|left|first) (?:monitor|screen|display)", base):
            return {"say": displays.set_mode("span")}
        if re.fullmatch(r"(?:always )?(?:keep|leave) (?:the )?(?:hud|stats|panel) (?:on|up)(?: on the other (?:monitor|screen))?|always on hud|always span", base):
            return {"say": displays.set_mode("span")}
        if re.fullmatch(r"dismiss(?: that| it)?|(?:hide|close|clear) (?:the other (?:monitor|screen)|the hud|the panel|other screen|the side screen)|hide that|(?:other|second) (?:monitor|screen) on demand|on demand (?:monitor|display|mode)", base):
            return {"say": displays.set_mode("ondemand") if "demand" in base else displays.dismiss()}
        m = re.fullmatch(r"(?:(?:switch to|use|show|open|go) (?:the )?)?(terminal|full|dense|compact|small|mini) (?:hud|side screen|second screen|monitor one panel)(?: mode)?", base)
        if m:
            st = "terminal" if m.group(1) in ("terminal", "full", "dense") else "compact"
            if config.get("display_mode") != "span": displays.set_mode("span")
            displays.show_temp(20, style=st); return {"say": displays.set_style(st)}
        if re.fullmatch(r"(?:single|one) (?:monitor|screen|display)(?: mode)?|just one (?:monitor|screen)|close the (?:hud|second screen|side hud)|turn off (?:the )?(?:hud|second screen)", base):
            return {"say": displays.set_mode("single")}
        return None

    # ------------------------------------------------------------ yes/no/send
    def clear_pending(self):
        if self.pending_confirm:
            actlog.write("DECLINED", self.pending_confirm["desc"], None, "cancelled")
        self.pending_confirm = None
        self.pending_yes = None

    def _special(self, t):
        base = t.strip(" ,.!")
        name = config.get("assistant_name").lower()
        if base in KILL or base in {f"{name} stop", f"stop {name}", f"{name} stop stop"} or base in set(config.get("kill_phrases") or []):
            self.clear_pending()
            tools._pending.update(text=None)
            if pc.power_pending():
                pc.cancel_power(quiet=True)
                return {"say": "Stopped. Power action cancelled.", "kill": True}
            return {"say": "Stopped.", "kill": True}
        if re.fullmatch(r"(?:please |vex |hey vex )?(?:open (?:up )?(?:everything|it all|all|the dashboard|dashboard|up)|show (?:me )?(?:the )?(?:dashboard|everything|it all|all|panels)|expand(?: (?:it|everything|the dashboard|dashboard))?|unfold(?: everything)?|full (?:dashboard|view)|open up)(?: please)?", base):
            config.set_view("full"); return {"say": "Opening everything up."}
        if re.fullmatch(r"(?:please |vex )?(?:minimi[sz]e(?: (?:it|everything|the dashboard|dashboard))?|just (?:the )?(?:ai|a i|you|orb|core)|collapse(?: (?:it|everything|the dashboard|dashboard))?|close (?:everything|it all|the dashboard|dashboard|up)|hide (?:the )?(?:dashboard|everything|panels)|ai only|orb only)(?: please)?", base):
            config.set_view("ai"); return {"say": "Back to just me."}
        m = re.fullmatch(r"(?:please )?(turn on|turn off|enable|disable|switch on|switch off|start|stop) (?:the |my )?(?:camera|webcam|cam)(?: please)?|(?:please )?(turn|switch) (?:the |my )?(?:camera|webcam) (on|off)", base)
        if m:
            on = not re.search(r"disable|off|stop", " ".join(x for x in m.groups() if x))
            config.save({"hand_control": on})
            return {"say": "Camera on for hand control. Point with your index finger, pinch to click." if on else "Camera off."}
        m = re.fullmatch(r"(?:please )?(enable|disable|turn on|turn off|start|stop|switch on|switch off) (?:the )?(?:hand|hands|gesture|finger|webcam hand) (?:control|controls|tracking|mode)(?: please)?", base) \
            or re.fullmatch(r"(?:please )?(turn|switch) (?:the )?(?:hand|gesture|finger) (?:control|controls|tracking|mode) (on|off)", base)
        if m:
            g = " ".join(x for x in m.groups() if x)
            on = not re.search(r"disable|off|stop", g)
            config.save({"hand_control": on})
            return {"say": "Hand control on. Point with your index finger, pinch to click." if on else "Hand control off. Camera's closed."}
        if pc.power_pending() and (base in CANCEL or base in NO or re.fullmatch(r"(?:cancel|abort|stop)(?: the)? (?:shutdown|shut down|restart|reboot|sleep|lock|countdown)|don'?t (?:shut ?down|restart|sleep|lock)(?: it| the pc)?", base)):
            return pc.cancel_power()
        if self.pending_confirm:
            pc_ = self.pending_confirm
            self.pending_confirm = None
            if time.time() - pc_["at"] < 60 and (base in CONFIRM_YES or re.fullmatch(r"(?:yes|yeah|yep)[, ]+(?:do it|go ahead|i'?m sure|send it|close it|delete it|run it)", base)):
                actlog.write("CONFIRMED", pc_["desc"], None, "User said: " + base)
                return pc_["fn"]()
            actlog.write("DECLINED", pc_["desc"], None, "User said: " + base)
            if base in NO or base in CANCEL or base in {"no don't", "nah don't", "no thanks", "don't"} or time.time() - pc_["at"] >= 60:
                return "Understood. I've left it alone."
            # anything else: drop the risky action and treat this as a new command
        r32 = self._v32(base, t)
        if r32 is not None:
            return r32
        if tools.has_pending_discord():
            if base in SEND or re.fullmatch(r"(?:yeah |yes |ok |okay )?(?:send|post)(?: it| that| the message)?(?: now)?", base):
                return tools.discord_send()
            if base in CANCEL or base in NO:
                return tools.discord_cancel()
        from . import resolve as _rs
        if _rs.PENDING["choice"]:
            r = _rs.answer_choice(base)
            if r is not None:
                return r
        if self.pending_yes:
            fn, self.pending_yes = self.pending_yes, None
            if base in YES or base.startswith(("yeah", "yes", "sure", "pull it")):
                return fn()
            if base in NO:
                return "All good."
        if base in ("goodnight", "good night", "goodnight vex", "good night vex", "night vex"):
            from . import ops
            return ops.goodnight()
        if base in SLEEP_WORDS:
            return {"say": random.choice(["Very good. I'll be here.", "Standing by, sir.", "As you wish. Call if you need me."]), "sleep": True}
        if base in SEND:
            return "There's nothing waiting to send."
        if base in CONFIRM_YES:
            return "Nothing is awaiting your approval at the moment."
        if base in NO:
            return "All good."
        return None

    # ------------------------------------------------------------ rule parser
    def _rules(self, t):
        from . import ops, assist as _as
        b = t.strip(" ,.!?")
        if re.fullmatch(r"(?:give me a |run a )?(?:status report|system status|sitrep)|how'?s (?:the|my) (?:system|pc|computer)(?: doing)?|systems? check", b):
            return ops.status_report()
        if re.fullmatch(r"(?:gaming mode|game mode|let'?s game|time to game)(?: on| please)?", b):
            return ops.gaming_mode()
        from . import extras as _ex, study as _st, settingsctl as _sc, pcindex as _pi
        m = re.fullmatch(r"(?:study|learn about|read up on|research and remember|go learn about|learn)\s+(?:about\s+)?(.+)", b)
        if m:
            return _st.study(m.group(1))
        m = re.fullmatch(r"what do you know about (.+)|what have you learned about (.+)|tell me what you know about (.+)", b)
        if m and not re.fullmatch(r"me|myself", (m.group(1) or m.group(2) or m.group(3))):
            topic = m.group(1) or m.group(2) or m.group(3)
            r = _st.recall(topic)
            if r:
                return r
            self.pending_yes = lambda: _st.study(topic)
            return f"Nothing in my notes on {topic} yet. Shall I study it?"
        # settings: read states (no changes)
        if re.fullmatch(r"what'?s (?:my |the )?(?:volume|sound level)(?: at)?|how loud is (?:it|my pc)|is (?:my )?(?:sound|audio|pc) muted", b):
            return _sc.report("volume")
        if re.fullmatch(r"what(?:'s| is) (?:my |the )?(?:default )?(?:audio|sound|output|speaker) (?:device|output)(?: set to)?|where is (?:my )?sound going", b):
            return _sc.report("volume")
        if re.fullmatch(r"(?:am i|are we) (?:on|connected to) (?:the )?(?:wi-?fi|wifi)|(?:wi-?fi|wifi) status|what (?:wi-?fi|wifi|network) am i on", b):
            return _sc.report("wifi")
        if re.fullmatch(r"is (?:my )?bluetooth (?:on|enabled|working)|bluetooth status", b):
            return _sc.report("bluetooth")
        if re.fullmatch(r"what(?:'s| is) (?:my |the )?power plan|which power plan(?: am i on)?", b):
            return _sc.report("power")
        if re.fullmatch(r"what(?:'s| is) my (?:screen |display |monitor )?resolution|display (?:info|status)|what are my displays?(?: set to)?", b):
            return _sc.report("display")
        if re.fullmatch(r"(?:settings|system settings) (?:status|report|check)|check my settings|read my settings", b):
            return _sc.report("all")
        m = re.fullmatch(r"(?:set|switch|change) (?:the |my )?power (?:plan|mode) to (.+)|switch to (high performance|balanced|power saver|ultimate performance)(?: mode| plan)?", b)
        if m:
            return _sc.set_power_plan(m.group(1) or m.group(2))
        # settings: open a page ("open sound settings", "bring up bluetooth settings", "device manager")
        m = re.fullmatch(r"(?:open|bring up|pull up|show me|go to|take me to)?\s*(?:the |my |windows )?(.+?)\s+(?:settings?|options|control panel|page)|(?:open|bring up|pull up) (?:the )?(settings|control panel|device manager|task manager|programs and features|power options|playback devices|network connections|disk management|environment variables|services|event viewer)", b)
        if m:
            q = (m.group(1) or m.group(2)).strip()
            hit, sc = _pi.find_setting(q + (" settings" if m.group(1) else ""))
            if hit and sc >= 0.8:
                try:
                    if tools.DRY_RUN:
                        return f"[dry-run] setting: {hit[0]} ({hit[1]})"
                    _pi.open_setting(hit[1])
                    from . import resolve as _rsv
                    _rsv.note(hit[0] + " settings", "setting")
                    return random.choice([f"{hit[0].title()} settings, sir.", f"Here are your {hit[0]} settings.", f"Opening {hit[0]} settings."]) if hit[1].startswith("ms-settings") else f"Opening {hit[0]}."
                except Exception as e:
                    return f"I couldn't open that page ({e})."
        from . import extras as _ex
        if re.fullmatch(r"what'?s on (?:my|the) screen|read (?:my|the) screen|what am i looking at|look at (?:my|the) screen|what do you see|describe (?:my|the) screen", b):
            if not b.startswith("read"):
                try:
                    v = _ex.look("Describe this image.")
                    if v:
                        try: ocr = ops.read_screen()
                        except Exception: ocr = ""
                        return _ex.plain_llm("Tell the user in two short spoken sentences what is on their screen: the main app or content, not the clock or date. Only mention things you are sure of. A small vision model described it as: "
                                             + v + "\nExact text read from the screen (trust this for names, numbers and times; the description can be wrong about details):\n" + ocr[:2000])
                except Exception:
                    log.exception("vision")
            return ops.describe_screen(_ex.plain_llm)
        if re.fullmatch(r"what'?s (?:this |the )?(?:song|track|playing|music)(?: called)?(?: right now| now)?|what song is (?:this|playing)|now playing|who'?s (?:this|singing)|what am i listening to", b):
            return _ex.now_playing()
        m = re.fullmatch(r"(?:play|put on|search) (.+?) on spotify|spotify (?:play |search )?(.+)", b)
        if m and not re.fullmatch(r"(?:pause|play|resume|stop|next|skip|previous|back)(?: song| track)?", (m.group(1) or m.group(2))):
            return _ex.spotify_search(m.group(1) or m.group(2))
        m = re.fullmatch(r"(summari[sz]e|explain|read(?: out| me)?|check|proofread|fix)(?: me)? (?:my |the |what'?s (?:in|on) (?:my |the ))?(?:clipboard|what i (?:just )?copied|the thing i copied)(?: for me)?", b)
        if m:
            task = {"summarise": "summarize", "proofread": "fix", "check": "fix"}.get(m.group(1), m.group(1).split()[0])
            return _ex.clipboard(task, _ex.plain_llm)
        if re.fullmatch(r"how'?s (?:my |the )?(?:youtube )?channel(?: doing)?|(?:youtube|channel) stats|how many (?:subs|subscribers) (?:do i have|have i got)|my sub(?:scriber)? count|check my channel", b):
            return _ex.channel_stats()
        if re.fullmatch(r"(?:run a |do a )?(?:status check|setup check|pre ?stream check|check my setup|stream check)|is (?:discord|obs|steam|steamvr|streamlabs)(?: and (?:discord|obs|steam|steamvr|streamlabs))? (?:running|open|on)", b):
            return _ex.status_check()
        m = re.fullmatch(r"remember (?:that )?(.+)", b)
        if m and not re.match(r"(?:to |me to )", m.group(1)):
            return _as.remember(m.group(1))
        if re.fullmatch(r"what do you (?:know|remember) about me|what have you remembered|list (?:my )?memories", b):
            mem = _as.memories()
            return ("Here's what I know, sir: " + "; ".join(x["text"] for x in mem[-8:]) + ".") if mem else "Nothing yet. Tell me 'remember that' and I'll keep it."
        m = re.fullmatch(r"(?:focus mode|do not disturb|quiet mode)(?: for (\d+) (minutes?|hours?))?", b)
        if m:
            n = int(m.group(1) or 1) * (60 if (m.group(2) or "hour").startswith("hour") else 1)
            config.save({"focus_until": time.time() + n * 60})
            return f"Very good. I'll keep quiet for {str(n // 60) + ' hour' + ('s' if n >= 120 else '') if n >= 60 else str(n) + ' minutes'} unless you call."
        if re.fullmatch(r"(?:good morning|morning|gm)(?: vex)?|(?:morning |daily )?briefing|brief me", t.strip(" ,.!?")):
            from . import product
            return product.brief(True)
        if re.search(r"\b(lights?|lamps?|bulbs?)\b", t):
            from . import smarthome
            kw = smarthome.parse(t)
            if kw:
                return smarthome.lights(**kw)
        # never go live / record
        if re.search(r"\b(go live|going live now|start (?:the |my )?(?:stream|streaming|broadcast|recording)|hit go live|press go live|start recording|record)\b", t) \
                and not re.search(r"\b(discord|tell|notify|message|say|type)\b", t):
            return tools.go_live_refusal()
        if re.search(r"\b(stop|end) (?:the |my )?(stream|streaming|recording|broadcast)\b", t):
            return "Ending the stream's on you, hit End Stream in Streamlabs so nothing gets cut off."

        m = re.match(r"^(?:type|write)\s+(?:out\s+)?(.+?)(?:\s+and\s+(?:then\s+)?(?:press|hit)\s+enter)?$", t)
        if m and not re.search(r"\b(?:in|on|into)\s+discord\b", t):
            out = [pc.type_into_focused(m.group(1))]
            if re.search(r"(?:press|hit)\s+enter$", t):
                out.append(pc.press_keys("enter"))
            return self._join(out) if len(out) > 1 else out[0]
        pre, msg = self._split_discord(t)
        if msg is not None:
            out = []
            if pre:
                r = self._clauses(pre)
                if r is None:
                    return None
                out.append(r)
            out.append(tools.discord_type(caps(msg)))
            return self._join(out)
        return self._clauses(t)

    def _split_discord(self, t):
        pats = [
            r"(?:notify|tell|message|text|let)\s+(?:everyone |people |them |the server |my server )?(?:in|on)\s+(?:the\s+)?discord\s+(?:know\s+)?(?:that\s+|saying\s+|:\s*)?(?P<m>.+)",
            r"(?:tell|message|notify)\s+discord\s+(?:that\s+|saying\s+)?(?P<m>.+)",
            r"let\s+discord\s+know\s+(?:that\s+)?(?P<m>.+)",
            r"(?:type|say|post|put|write|send)\s+(?:in|on|into)\s+(?:the\s+)?discord\s*(?:that\s+|saying\s+|:\s*)?(?P<m>.+)",
            r"(?:in|on)\s+discord\s+(?:say|type|post|write|tell them|tell everyone)\s+(?:that\s+)?(?P<m>.+)",
            r"(?:type|say|post|write)\s+(?P<m>.+?)\s+(?:in|on|into)\s+discord$",
        ]
        for p in pats:
            m = re.search(p, t)
            if m:
                pre = t[:m.start()].strip(" ,")
                pre = re.sub(r"\s*(?:,|\band then\b|\bthen\b|\band\b)\s*$", "", pre).strip()
                return pre, m.group("m").strip()
        return None, None

    def _join(self, replies):
        says, out = [], {}
        for r in replies:
            if isinstance(r, dict):
                says.append(r.get("say", ""))
                if r.get("after"): out["after"] = r["after"]
                if r.get("detail"): out["detail"] = (out.get("detail", "") + "\n" + r["detail"]).strip()
                if r.get("confirm") and "confirm" not in out:  # only one risky action can wait for "yes" at a time
                    out["confirm"], out["confirm_desc"] = r["confirm"], r.get("confirm_desc", "")
            else:
                says.append(r)
        out["say"] = " ".join(s for s in says if s)
        return out

    def _clauses(self, t):
        parts = [p.strip(" ,") for p in re.split(r"\s*(?:,\s*)?\b(?:and then|then|and also|also|and|plus)\b\s*|\s*,\s*", t) if p.strip(" ,")]
        if not parts:
            return None
        # "split steam and discord" / "snap X and Y" must stay one clause
        if re.match(r"(?:split|snap|put)\b", t) and len(parts) <= 3:
            r = self._one(t)
            return r
        results, open_names, last_verb = [], [], None
        for p in parts:
            kind, val = self._classify(p, last_verb)
            if kind is None:
                return None
            if kind == "open":
                open_names.extend(val); last_verb = "open"
                continue
            if open_names:
                results.append(tools.open_apps(open_names)); open_names = []
            last_verb = kind
            results.append(val() if callable(val) else val)
        if open_names:
            results.append(tools.open_apps(open_names))
        return results[0] if len(results) == 1 else self._join(results)

    def _one(self, t):
        kind, val = self._classify(t, None)
        if kind is None:
            return None
        if kind == "open":
            return tools.open_apps(val)
        return val() if callable(val) else val

    def _classify(self, p, last_verb):
        """Returns (kind, value). kind 'open' -> list of names; others -> callable/str."""
        r = self._classify_pc(p)
        if r:
            return r
        if re.search(r"\b(stream setup|set up (?:my |the )?stream|setup (?:my |the )?stream|get (?:my |the )?stream ready|start my stream|stream mode|prep (?:my |the )?stream|get ready to stream)\b", p):
            return "do", tools.stream_setup
        if re.fullmatch(r"(?:cancel|abort|stop)(?: the| my)? (?:shutdown|shut down|restart|reboot|power off)", p):
            return "do", pc.cancel_power
        if re.search(r"\block (?:my |the )?(?:screen|pc|computer)\b|^lock(?: it)?(?: up)?$", p):
            return "do", lambda: pc.power("lock")
        if re.search(r"\bunmute\b|\bmute\b(?! all)", p) and re.search(r"\b(volume|sound|pc|computer|audio|it)\b|^(?:un)?mute$", p):
            return "do", lambda: tools.volume("mute")
        if re.search(r"\b(volume|sound|audio|it) (?:up|louder)|\b(turn|crank) (?:it |the volume |volume |sound )?up\b|\blouder\b", p):
            return "do", lambda: tools.volume("up")
        if re.search(r"\b(volume|sound|audio|it) down|\bturn (?:it |the volume |volume |sound )?down\b|\bquieter\b|\blower (?:the )?volume\b", p):
            return "do", lambda: tools.volume("down")
        if re.search(r"\bwhat(?:'s| is) the time\b|\bwhat time is it\b|^time$|\bcurrent time\b", p):
            return "do", tools.tell_time
        if re.search(r"\bwhat(?:'s| is) (?:the date|today'?s date|today)\b|\bwhat day is it\b", p):
            return "do", tools.tell_date
        if re.search(r"\b(trending|what'?s hot|top sell|top games|popular games|what should i play|new games|what'?s popping)\b", p):
            return "do", lambda: tools.trending_report(True)
        if re.search(r"\b(what can you do|help|commands|what do you do)\b", p):
            return "do", lambda: "I can open your apps, split windows, switch Streamlabs scenes, type in Discord, check trending Steam games, change volume, and lock your PC. Check the Commands tab for the full list."
        if re.search(r"\b(windows?|screens?|apps?)\b.*\b(next to each other|side by side|split)\b|\bsplit (?:my |the )?(?:screen|windows?)\b", p) and not re.search(r"\block\b", p):
            return "do", lambda: tools.snap_windows()
        m = re.match(r"(?:split|snap|tile|put)\s+(?:the\s+)?(?:windows?|screens?|screen)?\s*(?:side by side|in half|left and right)?$", p)
        if m:
            return "do", lambda: tools.snap_windows()
        m = re.match(r"(?:split|snap|tile|put)\s+(?:the\s+)?(.+?)\s+(?:and|with|next to|&)\s+(.+?)(?:\s+(?:side by side|next to each other|left and right|on the screen))?$", p)
        if m:
            a, b = m.group(1), m.group(2)
            return "do", lambda: tools.snap_windows(a, b)
        m = re.search(r"(?:switch|change|swap|go|flip|set)\s+(?:the\s+)?(?:scene\s+)?(?:to\s+)?(?:the\s+)?(.+?)\s+scene$|(?:switch|change|set)\s+(?:the\s+)?scene\s+to\s+(?:the\s+)?(.+)$|^(.+?)\s+scene$", p)
        if m:
            name = next(g for g in m.groups() if g)
            return "do", lambda: tools.switch_scene(name)
        m = re.match(rf"{VERB_CLOSE}\s+(?:out\s+of\s+|down\s+)?(.+)$", p)
        if m:
            name = m.group(1)
            if re.search(r"^(?:this|it|that|this window|the window|current window)$", name):
                return "do", lambda: pc.window_action("", "close")
            return "do", lambda: tools.close_app(name)
        m = re.match(rf"{VERB_OPEN}\s+(?:up\s+)?(.+)$", p)
        if m:
            target = m.group(1).strip()
            if re.search(r"\b(steam )?(?:store )?page for (.+)$", target):
                g = re.search(r"page for (.+)$", target).group(1)
                return "do", lambda: tools.open_game_page(g)
            names = [n.strip() for n in re.split(r"\s*(?:,|&|\bplus\b)\s*", target) if n.strip()]
            key, info = tools.resolve_app(names[0])
            if info and all(tools.resolve_app(n)[1] for n in names):
                return "open", names
            if re.fullmatch(r"(?:it|that|the first one|the file|that file|the first|first one)", target):
                return "do", lambda: pc.open_found(0)
            m2 = re.fullmatch(r"(?:the )?(second|third|fourth|last) (?:one|file)", target)
            if m2:
                idx = {"second": 1, "third": 2, "fourth": 3, "last": -1}[m2.group(1)]
                return "do", lambda: pc.open_found(idx if idx >= 0 else len(pc._last_found["items"]) - 1)
            return "do", lambda: pc.open_anything(target)
        if last_verb == "open":
            key, info = tools.resolve_app(p)
            if info:
                return "open", [p]
        return None, None

    def _classify_pc(self, p):
        F = "desktop|documents|downloads|pictures|videos|music|projects|[a-j] drive|program files(?: x86)?|appdata|windows"
        m = re.fullmatch(r"(?:run|execute)(?: the| this| a)?(?: powershell| power shell| command| powershell command)\s+(.+)", p)
        if m:
            rm = re.search(r"(?:run|execute)(?: the| this| a)?(?: powershell| power shell| command| powershell command)\s+(.+)$", getattr(self, "_raw", ""), re.I | re.S)
            cmd = rm.group(1).strip() if rm else m.group(1)  # keep the original capitalization/quotes
            return "do", lambda: pc.run_powershell(cmd)
        if re.search(r"\b(?:take|grab|get|snap)?\s*(?:a\s+)?screen ?shot\b", p):
            return "do", pc.screenshot
        if re.fullmatch(r"(?:pause|play|resume|unpause)(?: the)?(?: music| song| video| it| spotify)?", p):
            return "do", lambda: pc.media("play_pause")
        if re.fullmatch(r"(?:skip|next)(?: the)?(?: song| track| video| one)?(?: please)?|play the next (?:song|track|video)", p):
            return "do", lambda: pc.media("next")
        if re.fullmatch(r"(?:previous|last|go back a|back)(?: the)? (?:song|track|video)|play the (?:previous|last) (?:song|track)", p):
            return "do", lambda: pc.media("previous")
        if re.fullmatch(r"stop the (?:music|song|video)", p):
            return "do", lambda: pc.media("stop")
        if re.search(r"\b(?:shut ?down|turn off|power off) (?:my |the )?(?:pc|computer)\b|^shut ?down$", p):
            return "do", lambda: pc.power("shutdown")
        if re.search(r"\b(?:restart|reboot) (?:my |the )?(?:pc|computer)\b|^(?:restart|reboot)$", p):
            return "do", lambda: pc.power("restart")
        if re.search(r"\b(?:sign|log) (?:me )?out\b", p):
            return "do", lambda: pc.power("sign_out")
        if re.search(r"\bput (?:my |the )?(?:pc|computer) to sleep\b|^sleep mode$|^sleep (?:my |the )?(?:pc|computer)$", p):
            return "do", lambda: pc.power("sleep")
        if re.search(r"\b(clean|clear|free|make|fix|improve|empty)\b.*\b(disk|storage|space|drive|c drive)\b|\bmore (?:disk )?space\b|\bgive me more\b.*space", p):
            return "do", pc.clean_disk
        m = re.match(r"(?:text|message|notify|ping) (?:my phone|me)(?: (?:that|saying|with|to say))?[:, ]*(.*)$|send (?:a )?(?:text|message|notification|note|it|this|that)? ?to my phone(?: (?:that|saying))?[:, ]*(.*)$", p)
        if m and not re.search(r"\d{3}[\s.-]?\d{3}[\s.-]?\d{4}", p):
            from . import notify
            msg = (m.group(1) or m.group(2) or "").strip() or "Ping from Vex."
            return "do", lambda: notify.push(msg)
        if re.search(r"\b(?:text|sms|imessage|call|ring|message)\b.*(?:\d{3}[\s.-]?\d{3}[\s.-]?\d{4}|\b(?:mom|dad|him|her|them|my friend)\b)", p):
            return "say", "I can only send notifications to your own phone, sir. Texting other numbers or contacts is off-limits. Say 'text my phone' and the message."
        if re.search(r"\b(battery|disk space|storage|free space|how much space|space left|ram|memory|cpu|gpu|temps?|temperature|"
                     r"what'?s running|what(?:'s| is| apps are) open|uptime|been on|internet|ping)\b", p) and \
                not re.match(r"(?:open|close|find|delete|move|copy|rename|explain|why|how (?:does|do|did|is|are)|what (?:is|are) (?:a |an |the )?(?:cpu|gpu|ram)|tell me about|teach)\b", p):
            return "do", lambda: pc.system_info(p)
        if re.fullmatch(r"(?:minimi[sz]e (?:everything|all(?: windows)?)|show (?:me )?(?:my |the )?desktop)", p):
            return "do", pc.minimize_all
        m = re.fullmatch(r"(minimi[sz]e|maximi[sz]e|restore|focus|switch to|full ?screen)\s*(.*)", p)
        if m and not p.endswith("scene"):
            act = {"switch to": "focus", "fullscreen": "maximize", "full screen": "maximize"}.get(m.group(1), m.group(1))
            app = m.group(2)
            return "do", lambda: pc.window_action(app, act)
        m = re.fullmatch(rf"(?:find|search for|look for|locate|where'?s|where is)\s+(?:my |the )?(.+?)(?:\s+(?:in|on) (?:my |the )?({F}))?(?: folder)?", p)
        if m and not re.search(r"\bon steam\b", p):
            name, where = m.group(1), m.group(2)
            return "do", lambda: pc.find(name, where)
        m = re.fullmatch(r"show (?:me )?(.+?) in (?:file )?(?:explorer|the folder|its folder|folder)", p)
        if m:
            return "do", lambda: pc.show_in_folder(m.group(1))
        m = re.fullmatch(r"(?:bring|pull)(?: up)? (.+?)(?: up)?(?: (?:on|to) (?:my |the )?(?:second |2nd |other |main )?(?:monitor|screen))?|(?:bring|pull) (?:this|that|it) up|(?:bring|pull) up|show me (.+)", p)
        if m and not re.search(r"\b(weather|forecast|time|date|news|reminders?|tasks?|to ?dos?|stats|status|memor(?:y|ies)|calendar)\b", p):
            from . import resolve
            target = (m.group(1) or m.group(2) or "").strip()
            if re.fullmatch(r"(?:this|that|it)", target):
                target = ""
            return "do", lambda: resolve.bring_up(target)
        m = re.fullmatch(r"(?:make|create|new)\s+(?:me\s+)?(?:a\s+)?(?:new\s+)?folder(?:\s+(?:called|named))?\s+(.+?)(?:\s+(?:on|in)\s+(?:my |the )?(.+))?", p)
        if m:
            name, where = m.group(1), m.group(2) or "desktop"
            return "do", lambda: pc.create_folder(name, where)
        m = re.fullmatch(r"(move|copy)\s+(.+?)\s+(?:to|into)\s+(?:my |the )?(.+?)(?: folder)?", p)
        if m:
            verb, name, to = m.groups()
            return "do", (lambda: pc.move_item(name, to)) if verb == "move" else (lambda: pc.copy_item(name, to))
        m = re.fullmatch(r"rename\s+(.+?)\s+to\s+(.+)", p)
        if m:
            a, b = m.groups()
            return "do", lambda: pc.rename_item(a, b)
        m = re.fullmatch(r"(?:delete|trash|recycle|get rid of|throw away|remove the file|remove the folder)\s+(.+)", p)
        if m:
            name = m.group(1)
            return "do", lambda: pc.recycle_item(name)
        m = re.fullmatch(r"(?:press|hit|push|do)\s+(.+?)(?:\s+key)?", p)
        if m and m.group(1) not in ("go live", "the go live button") and winutil_combo_ok(m.group(1)):
            keys = m.group(1)
            return "do", lambda: pc.press_keys(keys)
        m = re.fullmatch(r"(double |right |middle )?click(?: (?:at|on))?(?: (\d+)[ ,x]+(\d+))?(?: (?:in )?(?:the )?(middle|center)(?: of the (?:window|screen))?)?(?: it| that)?", p)
        if m:
            kind, x, y, where = m.groups()
            kind = (kind or "").strip()
            return "do", lambda: pc.mouse_click("right" if kind == "right" else "middle" if kind == "middle" else "left", kind == "double",
                                                int(x) if x else None, int(y) if y else None, "center" if where else None)
        return None

    # ------------------------------------------------------------ LLM
    def _system(self):
        name = config.get("assistant_name")
        now = datetime.datetime.now().strftime("%A %I:%M %p")
        who = config.get('user_name') or "the user"
        return (f"You are {name}, a voice assistant on {who}'s Windows PC. "
                f"Speak like a dry, witty, warm British butler AI: calm, understated and confident, talking naturally with contractions (I'm, you're, it's) and short conversational sentences, occasionally (not every time) addressing them as 'sir', with clean language and no swearing. Reply in one or two short sentences, "
                f"no emojis, no lists, no markdown, because your reply is spoken out loud. Use the tools to do things on the PC; "
                f"never say you did something unless you called a tool. You cannot go live, start or stop recording, buy anything, "
                f"sign in to accounts, delete files, or text/call other people (you CAN push a notification to their own phone and you CAN type, press keys and click); if asked, say so in one sentence. Never claim something was sent or done unless a tool did it. Discord messages are only typed, "
                f"they say 'send' to post them. They gave you full access to their PC (any drive, app, setting, PowerShell). Risky actions (deleting, closing apps, pressing Enter "
                f"in chats, shutdown, settings changes, PowerShell that changes things, writes in Windows/Program Files) automatically ask them "
                f"to say yes, so just call the tool. For Windows settings use run_powershell (or open_anything with an ms-settings page). It is {now}.\n"
                f"Examples of your style:\nUser: yo what's up\nYou: All quiet on my end, sir. What shall we do?\n"
                f"User: tell me a joke\nYou: I would, but my timing is strictly digital.\n"
                f"User: I'm bored\nYou: Might I suggest a game, or shall I see what's trending on Steam?") + __import__("vex.modes", fromlist=["x"]).prompt_hint()

    def _remember(self, user, reply):
        self.history.append({"role": "user", "content": user})
        if reply:
            self.history.append({"role": "assistant", "content": reply})
        self.history = self.history[-20:]

    def _llm(self, text):
        eng = getattr(self, "engine", None)
        if eng is not None:  # Vex 2.0: shared general-assistant brain with tools (voice mode = short spoken reply)
            r = eng.ask(text, self.history[-20:], "voice")
            r.pop("detail", None) if not r.get("confirm") else None
            say = r.get("say", "")
            r["say"] = " ".join(re.split(r"(?<=[.!?])\s+", say)[:3]) or "Say that again?"
            return r
        msgs = [{"role": "system", "content": self._system()}] + self.history[-20:] + [{"role": "user", "content": text}]
        try:
            if config.get("llm_backend") == "openai_compatible" and config.get("api_key") and config.get("api_base_url"):
                content, calls = self._openai(msgs)
            else:
                content, calls = self._ollama(msgs)
        except Exception as e:
            log.warning("LLM failed: %s", e)
            return "My brain's still loading, give me a sec and try again."
        if calls:
            replies = [tools.run_tool(n, a) for n, a in calls[:4]]
            return self._join(replies)
        content = re.sub(r"[*_#`]", "", (content or "").strip())
        sentences = re.split(r"(?<=[.!?])\s+", content)
        return " ".join(sentences[:2]) or "Say that again?"

    def _post(self, url, body, headers=None, timeout=60):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **(headers or {})})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def _ollama(self, msgs):
        body = {"model": config.get("ollama_model"), "messages": msgs, "tools": tools.all_tools()[1], "stream": False,
                "keep_alive": self.keep_alive, "options": self._opts({"temperature": 0.4, "num_ctx": 4096, "num_predict": 120})}
        r = self._post(config.get("ollama_url").rstrip("/") + "/api/chat", body)
        m = r.get("message", {})
        calls = []
        for c in m.get("tool_calls") or []:
            f = c.get("function", {})
            args = f.get("arguments") or {}
            if isinstance(args, str):
                try: args = json.loads(args)
                except Exception: args = {}
            calls.append((f.get("name"), args))
        return m.get("content", ""), calls

    def _openai(self, msgs):
        body = {"model": config.get("api_model") or "gpt-4o-mini", "messages": msgs, "tools": tools.all_tools()[1], "max_tokens": 150}
        r = self._post(config.get("api_base_url").rstrip("/") + "/chat/completions", body, {"Authorization": "Bearer " + config.get("api_key")})
        m = r["choices"][0]["message"]
        calls = []
        for c in m.get("tool_calls") or []:
            try: args = json.loads(c["function"].get("arguments") or "{}")
            except Exception: args = {}
            calls.append((c["function"]["name"], args))
        return m.get("content") or "", calls

    def _opts(self, o):
        o = dict(o, num_ctx=int(config.get("llm_ctx") or 4096))  # same context size everywhere so Ollama doesn't reload the model
        if self.cpu_only:
            o["num_gpu"] = 0
        return o

    def warmup(self):
        """Loads the model into memory so the first real command is fast."""
        try:
            model = config.get("ollama_fast_model") or config.get("ollama_model")
            try:
                from .chat import Engine
                if not Engine._have_model(Engine, model):
                    model = config.get("ollama_model")
            except Exception:
                pass
            msgs = [{"role": "user", "content": "hi"}]
            body = {"model": model, "stream": False, "keep_alive": -1 if not self.cpu_only else "30m", "options": self._opts({"num_predict": 1})}
            try:  # 4.2 speed: also primes Ollama's prompt cache with the voice system prompt + base tools
                from . import chat
                f, sch = chat.pick_tools("", "local")
                msgs = [{"role": "system", "content": chat.voice_prompt()}] + msgs
                body["tools"] = chat.voice_tools("", sch)
            except Exception:
                pass
            body["messages"] = msgs
            t0 = time.time()
            self._post(config.get("ollama_url").rstrip("/") + "/api/chat", body, timeout=180)
            log.info("fast model %s warm (%s) in %.1f s", model, "CPU" if self.cpu_only else "GPU", time.time() - t0)
            return True
        except Exception as e:
            log.info("warmup failed: %s", e)
            return False

    def unload(self):
        """Frees the models from GPU/RAM right now (fast + big)."""
        ok = False
        for m in {config.get("ollama_model"), config.get("ollama_fast_model")} - {None, ""}:
            try:
                self._post(config.get("ollama_url").rstrip("/") + "/api/generate", {"model": m, "keep_alive": 0}, timeout=30)
                ok = True
            except Exception:
                pass
        return ok
