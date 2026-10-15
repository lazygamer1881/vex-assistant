"""Vex 2.0 brain: chat + voice answers with tools. Local Ollama by default, optional cloud brains when a key is set."""
import os, re, json, time, uuid, secrets, datetime, logging, threading, urllib.request, urllib.error
from . import config, tools, assist, actlog

log = logging.getLogger("vex.chat")
CHATS = os.path.join(assist.DATA, "chats")

PROVIDERS = {  # name: (base url, default model)
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "anthropic": ("https://api.anthropic.com/v1", "claude-haiku-4-5"),
    "openrouter": ("https://openrouter.ai/api/v1", "openrouter/auto"),
    "lmstudio": ("http://127.0.0.1:1234/v1", "local-model"),
}
STREAM_WORDS = re.compile(r"\b(stream|streaming|obs|streamlabs|scene|go live|discord|twitch|steam|trending)\b", re.I)
PC_TOOLS_CORE = {"open_anything", "window_action", "show_desktop", "type_text", "press_keys", "media_control", "find_files", "open_found_file",
                 "create_folder", "move_item", "copy_item", "rename_item", "recycle_item", "screenshot", "system_info", "run_powershell", "power",
                 "open_apps", "close_app", "snap_windows", "lock_screen", "set_volume", "tell_time", "tell_date", "mouse_click"}
STREAM_TOOLS = {"switch_scene", "discord_type_message", "trending_games", "open_steam_game_page", "stream_setup"}


def active_brain():
    """Which brain answers: first cloud provider with a key (unless forced local), else local Ollama."""
    pref = config.get("brain") or "auto"
    if pref == "local":
        return "local"
    order = [pref] if pref in PROVIDERS else ["groq", "gemini", "openai", "anthropic"]
    for p in order:
        if config.get(p + "_key"):
            return p
    if config.get("llm_backend") == "openai_compatible" and config.get("api_key") and config.get("api_base_url"):
        return "custom"
    return "local"


def brain_label(b=None):
    b = b or active_brain()
    if b == "local":
        return "Local · " + config.get("ollama_model")
    if b in ("webhook",):
        return "Custom agent"
    if b == "custom":
        return "API · " + (config.get("api_model") or "custom")
    return b.capitalize() + " · " + (config.get(b + "_model") or PROVIDERS[b][1])


def system_prompt(mode):
    name, user = config.get("assistant_name"), (config.get("user_name") or "the user")
    now = datetime.datetime.now().strftime("%A, %B %d %Y, %I:%M %p")
    base = (f"You are {name}, {user}'s personal AI assistant on their Windows PC. They mostly want a "
            f"general helper. Personality: a dry, witty, impeccably polite British butler-style AI. Short, confident replies; understated humour; address them as sir only occasionally (at most once every few replies). Offer brief proactive remarks when useful (for example: the drive is nearly full, or rain is due later). Never sarcastic at their expense. Keep everything age-appropriate: no swearing, no adult "
            f"content, nothing dangerous; if something isn't okay, say so kindly and help with something else.\n"
            f"You can: answer questions, research the web, help with homework, writing, and coding, remember things, set reminders and to-dos, "
            f"read files, check weather, and control the PC with tools. Use tools whenever they help; for anything current (news, scores, prices, "
            f"releases, facts you're unsure of) call web_search first and say where the info came from. Never say you did something unless a tool did it."
            f" You can send a push notification to the user's OWN phone with notify_my_phone (for 'text my phone' / 'send me'), but you cannot text, email or call anyone else or any number, and you must never write code (Telethon, Twilio, smtplib, etc.) to try. Never claim something was sent, deleted, installed or done unless a tool result says so. You cannot play games for them (no in-game actions like breeding villagers), but you can control their keyboard and mouse: open apps, type text, press keys and shortcuts, and click (risky ones ask first). For game facts (Minecraft recipes, builds, game updates) call web_search first and cite it; if you're not sure, say so instead of guessing. For freeing disk space use the clean_disk tool; never delete program, game or Windows files. Keep answers short unless they ask for detail.\n"
            f"Rules you can't break: never buy anything, never sign in to accounts, never start streams or recordings. Risky actions (deleting, sending, "
            f"system changes, running code) automatically ask {user} for a yes, so just call the tool. If {user} says 'remember' something, call remember.\n"
            f"Homework: explain step by step so they learn it; show the work and check the final answer. Writing: help improve their own writing, keep their voice. "
            f"Coding: give working code in code blocks, explain briefly; use run_python to test when useful.\nNow: {now}.")
    mem = assist.memory_prompt()
    if mem:
        base += "\n" + mem
    base += ("\nConversation style: talk like a real person in a back-and-forth, not a command line. Use the earlier turns: "
             "when he says 'it', 'that', 'the game' or 'him', work out what he means from the conversation and don't ask again if it's clear. "
             "Vary your wording and openings; never start two replies the same way, and don't repeat a phrase you used recently. "
             "Be warm, with the occasional dry joke, but don't force one every time. When it helps, end with one short follow-up question "
             "(not every reply). If he's vague, ask one quick clarifying question instead of guessing.")
    try:
        from . import resolve
        if resolve.LAST.get("name"):
            base += f"\nThe last thing mentioned or opened was: {resolve.LAST['name']} ({resolve.LAST['kind']})."
    except Exception:
        pass
    if mode == "voice":
        base += ("\nYour reply is spoken out loud: one to three short sentences, no markdown, no lists, no emojis, no URLs. "
                 "Lead with the answer, then (only when natural) a brief offer. Examples of your voice:\n"
                 "User: what's 15 percent of 80\nYou: Twelve, sir.\n"
                 "User: I'm bored\nYou: Tragic. Shall I open a game, or see what's trending on Steam?\n"
                 "User: is it going to rain\nYou: Forty percent chance this afternoon. An umbrella wouldn't go amiss.\n"
                 "User: you're slow\nYou: Thinking takes a moment, even for me. What can I do for you?\n"
                 "User: thanks\nYou: Always a pleasure.\n"
                 "User: I just finished editing the new map video\nYou: Splendid. How did it turn out?\n"
                 "User: pretty good, uploading it tonight\nYou: Then the internet is in for a treat. Want a reminder to check the comments tomorrow?")
    else:
        base += "\nYou're in a chat window: use Markdown (headings, lists, **bold**, tables, ```code blocks```) when it helps. Keep casual answers short."
    return base


HARD = re.compile(r"\b(explain|in detail|step by step|essay|paragraph|code|script|program|debug|homework|solve|equation|summari[sz]e|analy[sz]e|"
                  r"story|poem|translate|compare|pros and cons|research|write (?:me )?(?:a|an|some))\b", re.I)


def is_hard(text):
    """4.2 speed: quick chat goes to the small fast model; real thinking goes to the big one."""
    t = text or ""
    return (bool(HARD.search(t)) and len(t.split()) >= 4) or len(t.split()) >= 18


def looks_broken(say):
    """A reply that's mostly URL-encoding / one giant token: retry with the other model."""
    s = say or ""
    return bool(re.search(r"%[0-9A-Fa-f]{2}.*%[0-9A-Fa-f]{2}", s)) or (len(s) > 40 and s.count(" ") < len(s) / 25)


VOICE_GROUPS = [  # 4.2 speed: voice turns only carry the tools the sentence could need (fewer tokens = faster first word)
    (r"\b(open|launch|start|close|quit|window|snap|split|minimi|maximi|bring up|pull up|switch to)", {"open_apps", "close_app", "snap_windows", "window_action", "open_anything"}),
    (r"\b(type|press|key|shortcut|click)", {"type_text", "press_keys"}),
    (r"\b(music|song|play|pause|skip|next track|volume|louder|quieter|mute|spotify)", {"media_control", "now_playing", "set_volume"}),
    (r"\b(file|folder|document|move|rename|delete|recycle|read)", {"find_files", "create_folder", "move_item", "rename_item", "recycle_item", "read_file"}),
    (r"\b(cpu|ram|memory|disk|drive|gpu|storage|shut ?down|restart|reboot|sleep|lock|screenshot|powershell|setting|clean|space)", {"system_info", "run_powershell", "power", "clean_disk", "lock_screen", "screenshot"}),
    (r"\b(website|url|link|article|research|look up|news|latest)", {"read_webpage", "research"}),
    (r"\b(to ?do|task|reminders?|timer)", {"add_todo", "list_todos", "complete_todo", "list_reminders", "cancel_reminder"}),
    (r"\bforget\b", {"forget"}),
    (r"\b(phone|notify|text me|send me)", {"notify_my_phone"}),
    (r"\b(subs|subscribers?|channel|stream|youtube|obs|streamlabs|discord|steam)", {"youtube_channel_stats", "setup_status_check"}),
    (r"\b(python|calculate|compute|math)", {"run_python"}),
    (r"\b(lights?|lamps?)\b", {"smart_lights"}),
]
VOICE_BASE = {"web_search", "get_weather", "remember", "set_reminder", "open_anything"}


def voice_tools(text, sch):
    want = set(VOICE_BASE)
    for pat, names in VOICE_GROUPS:
        if re.search(pat, text or "", re.I):
            want |= names
    return [x for x in sch if x["function"]["name"] in want]


def voice_prompt():
    """4.2 speed: short, stable system prompt for spoken turns (stable text = Ollama reuses its prompt cache)."""
    name, user = config.get("assistant_name"), (config.get("user_name") or "the user")
    p = (f"You are {name}, {user}'s voice assistant on their Windows PC. Personality: a dry, witty, warm British butler AI - calm, confident, "
         f"contractions, short natural sentences, occasionally calling them 'sir'. Clean, friendly language. Your reply is spoken: one or two short "
         f"sentences, answer first, no lists, markdown, emojis or URLs. Use tools to act on the PC or look things up (web_search for anything current); "
         f"never claim you did something unless a tool did it. Never buy anything, sign in to accounts, or start streams or recordings. "
         f"Risky actions ask for a yes automatically, so just call the tool. If they say 'remember', call remember.")
    try:
        m = [x["text"] for x in assist.memories()[-12:]]
        if m:
            p += "\nThings you remember about them: " + "; ".join(m)
    except Exception:
        pass
    return p


def pick_tools(text, brain):
    funcs, schema = tools.all_tools()
    funcs = {**funcs, **assist.FUNCS}
    allowed = set(assist.FUNCS) | PC_TOOLS_CORE
    if STREAM_WORDS.search(text or ""):
        allowed |= STREAM_TOOLS
    sch = [s for s in schema + assist.SCHEMA if s["function"]["name"] in allowed]
    if brain == "local":  # small model: fewer tools = better choices
        sch = [s for s in sch if s["function"]["name"] not in {"mouse_click", "show_desktop", "open_found_file", "copy_item", "tell_date", "list_memories", "morning_briefing"}]
    return funcs, sch


def _post(url, body, headers=None, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:300].decode('utf8', 'replace')}")


class Engine:
    def __init__(self, brain_obj=None):
        self.voice_brain = brain_obj  # core Brain (for keep_alive / cpu_only)
        self.pending = None  # {"id","fn","desc","at","chat"}
        self.lock = threading.Lock()
        self.status_cb = None
        self.last_brain = "local"
        self.sink = None  # Vex 4.2: callable(sentence) - voice replies are spoken sentence by sentence while still generating

    # ---------------------------------------------------------------- providers
    _models = {"t": 0, "names": set()}

    def _have_model(self, name):
        """Is this model downloaded in Ollama? (cached for a minute)"""
        M = Engine._models
        if time.time() - M["t"] > 60:
            try:
                with urllib.request.urlopen(config.get("ollama_url").rstrip("/") + "/api/tags", timeout=3) as r:
                    M["names"] = {m.get("name", "") for m in json.loads(r.read()).get("models", [])}
                M["t"] = time.time()
            except Exception:
                return True
        return any(n == name or n == name + ":latest" or n.split(":")[0] == name for n in M["names"])

    def _stream_local(self, body, sink):
        """Vex 4.2: streams the Ollama reply and hands each finished sentence to sink() right away,
        so speech starts while the rest is still generating. Tool calls are collected as usual."""
        self._streamed = 0
        req = urllib.request.Request(config.get("ollama_url").rstrip("/") + "/api/chat", data=json.dumps(dict(body, stream=True)).encode(),
                                     headers={"Content-Type": "application/json"})
        content, calls, buf, spoken, held = "", [], "", 0, False
        t0 = time.time()

        def clean(x):
            x = re.sub(r"```.*?```", "", x, flags=re.S)
            x = re.sub(r"[*_#`>|]", "", x)
            return re.sub(r"https?://\S+", "", x).strip()

        with urllib.request.urlopen(req, timeout=240) as r:
            for line in r:
                line = line.strip()
                if not line:
                    continue
                try:
                    j = json.loads(line.decode("utf-8", "replace"))
                except Exception:
                    continue
                msg = j.get("message") or {}
                if msg.get("tool_calls"):
                    calls += msg["tool_calls"]
                piece = msg.get("content") or ""
                content += piece
                if not held and content.lstrip()[:1] in ("{", "[", "`"):
                    held = True  # looks like a tool call printed as text: don't speak it
                if piece and not held and not calls and spoken < 3:
                    buf += piece
                    while spoken < 3:
                        mm = re.search(r"^(.+?[.!?])(?:[\s\"')\]]+)(?=\S)", buf, re.S)
                        if not mm or len(mm.group(1)) < 4:
                            break
                        sent = clean(mm.group(1)); buf = buf[mm.end():]
                        if sent:
                            if not spoken:
                                log.info("first sentence streamed in %.1f s", time.time() - t0)
                            sink(sent); spoken += 1; self._streamed = spoken
                if j.get("done"):
                    break
        if spoken and not calls and not held and spoken < 3:
            tail = clean(buf)
            if tail:
                sink(tail); spoken += 1; self._streamed = spoken
        return {"content": content, "tool_calls": calls}

    def _call(self, brain, msgs, sch, mode):
        maxtok = 220 if mode == "voice" else 1500
        if brain == "local":
            om = []
            for m in msgs:
                m = dict(m)
                if m.get("tool_calls"):
                    m["tool_calls"] = [{"function": {"name": c["function"]["name"], "arguments": json.loads(c["function"]["arguments"] or "{}")}} for c in m["tool_calls"]]
                m.pop("tool_call_id", None)
                om.append(m)
            o = {"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.15, "num_predict": maxtok, "num_ctx": int(config.get("llm_ctx") or 4096)}
            vb = self.voice_brain
            model, keep = config.get("ollama_model"), getattr(vb, "keep_alive", "15m")
            fastm = config.get("ollama_fast_model")
            if fastm and not self._have_model(fastm):
                fastm = None                     # fast model not downloaded: use the main one
            if vb is not None and vb.cpu_only:
                o["num_gpu"] = 0
                model = fastm or config.get("ollama_model_light") or model  # game/VR running: small model on CPU stays responsive
            elif mode == "voice" and fastm and not getattr(self, "_hard", False):
                model, keep = fastm, -1          # the fast model stays loaded forever
            elif mode == "voice" and fastm:
                keep = "10m"                     # big model for hard questions, unloads after a while
            self.last_model = model
            body = {"model": model, "messages": om, "stream": False, "options": o, "keep_alive": keep}
            if sch:
                body["tools"] = sch
            if model != fastm and fastm and not self._have_model(model):
                model, keep = fastm, -1          # big model not downloaded: the fast one answers everything
                body["model"], body["keep_alive"] = model, keep
                self.last_model = model
            sink = self.sink if (mode == "voice" and om and om[-1].get("role") == "user" and config.get("stream_replies") is not False) else None
            if sink:
                try:
                    m = self._stream_local(body, sink)
                except Exception as e:
                    log.info("stream failed, falling back: %s", e)
                    if getattr(self, "_streamed", 0):
                        raise
                    m = _post(config.get("ollama_url").rstrip("/") + "/api/chat", dict(body, stream=False), timeout=240).get("message", {})
            else:
                r = _post(config.get("ollama_url").rstrip("/") + "/api/chat", body, timeout=240)
                m = r.get("message", {})
            calls = []
            for c in m.get("tool_calls") or []:
                f = c.get("function", {}); a = f.get("arguments") or {}
                if isinstance(a, str):
                    try: a = json.loads(a)
                    except Exception: a = {}
                calls.append({"id": "c" + uuid.uuid4().hex[:6], "name": f.get("name"), "args": a})
            content = m.get("content") or ""
            if not calls:  # small models sometimes print the tool call as JSON text
                j = re.search(r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"(?:arguments|parameters)"\s*:\s*(\{.*?\})\s*\}', content, re.S)
                if j and any(s["function"]["name"] == j.group(1) for s in sch or []):
                    try:
                        calls.append({"id": "c1", "name": j.group(1), "args": json.loads(j.group(2))}); content = ""
                    except Exception:
                        pass
            return content, calls
        if brain == "anthropic":
            return self._anthropic(msgs, sch, maxtok)
        if brain == "custom":
            base, key, model = config.get("api_base_url").rstrip("/"), config.get("api_key"), config.get("api_model") or "gpt-4o-mini"
        else:
            base, model = PROVIDERS[brain][0], config.get(brain + "_model") or PROVIDERS[brain][1]
            key = config.get(brain + "_key")
            if brain == "lmstudio":
                base, key = (config.get("lmstudio_url") or base).rstrip("/"), "lm-studio"
        body = {"model": model, "messages": msgs, "max_tokens": maxtok}
        if sch:
            body["tools"] = sch
        r = _post(base + "/chat/completions", body, {"Authorization": "Bearer " + key}, timeout=90)
        m = r["choices"][0]["message"]
        calls = []
        for c in m.get("tool_calls") or []:
            try: a = json.loads(c["function"].get("arguments") or "{}")
            except Exception: a = {}
            calls.append({"id": c.get("id") or "c1", "name": c["function"]["name"], "args": a or {}})
        return m.get("content") or "", calls

    def _anthropic(self, msgs, sch, maxtok):
        system = "\n".join(m["content"] for m in msgs if m["role"] == "system")
        out = []
        for m in msgs:
            if m["role"] == "system":
                continue
            if m["role"] == "tool":
                blk = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(blk)
                else:
                    out.append({"role": "user", "content": [blk]})
            elif m.get("tool_calls"):
                blocks = ([{"type": "text", "text": m["content"]}] if m.get("content") else []) + [
                    {"type": "tool_use", "id": c["id"], "name": c["function"]["name"], "input": json.loads(c["function"]["arguments"] or "{}")} for c in m["tool_calls"]]
                out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": m["role"], "content": m["content"] or "..."})
        body = {"model": config.get("anthropic_model") or PROVIDERS["anthropic"][1], "max_tokens": maxtok, "system": system, "messages": out}
        if sch:
            body["tools"] = [{"name": s["function"]["name"], "description": s["function"]["description"], "input_schema": s["function"]["parameters"]} for s in sch]
        r = _post("https://api.anthropic.com/v1/messages", body, {"x-api-key": config.get("anthropic_key"), "anthropic-version": "2023-06-01"}, timeout=90)
        text = "".join(b.get("text", "") for b in r["content"] if b["type"] == "text")
        calls = [{"id": b["id"], "name": b["name"], "args": b.get("input") or {}} for b in r["content"] if b["type"] == "tool_use"]
        return text, calls

    # ---------------------------------------------------------------- main loop
    def ask(self, text, history=None, mode="chat", chat_id=None, brain=None):
        """Returns dict(say, detail, confirm, confirm_desc, after, brain, tools)."""
        if brain is None:
            brain = active_brain()
            try:
                from . import connections as _cn
                hp = config.get("hard_provider")
                if hp and hp in PROVIDERS and _cn.configured(hp) and _cn.is_hard(text):
                    brain = hp
            except Exception:
                pass
        try:
            return self._ask(brain, text, history, mode, chat_id)
        except Exception as e:
            if brain != "local":
                log.warning("%s failed, falling back to local: %s", brain, e)
                r = self._ask("local", text, history, mode, chat_id)
                r["note"] = f"{brain} didn't answer, used the local brain."
                return r
            log.warning("local LLM failed: %s", e)
            return {"say": "My brain's still loading or Ollama isn't running. Give me a sec and try again.", "brain": brain, "error": str(e)}

    def _ask(self, brain, text, history, mode, chat_id):
        self.last_brain = brain
        funcs, sch = pick_tools(text, brain)
        fast = mode == "voice" and brain == "local" and config.get("ollama_fast_model")
        self._hard = mode == "voice" and config.get("route_hard") is not False and is_hard(text)
        extra = ""
        if fast:
            sp = voice_prompt()
            sch = voice_tools(text, sch)
            hist = list(history or [])[-8:]
        else:
            sp = system_prompt(mode)
            hist = list(history or [])[-20:]
        try:  # Vex 4.2: older memories that match this question
            recent = {x["text"] for x in assist.memories()[-(12 if fast else 30):]}
            rel = [m for m in assist.relevant_memories(text, 4 if fast else 6) if m not in recent]
            if rel:
                extra += "\n(Possibly relevant memories: " + "; ".join(rel) + ")"
        except Exception:
            pass
        try:
            from . import study
            c = study.context_for(text)
            if c:
                extra += "\n" + c.strip()
        except Exception:
            pass
        if fast:
            extra += datetime.datetime.now().strftime("\n(Now: %A %I:%M %p)")
            msgs = [{"role": "system", "content": sp}] + hist + [{"role": "user", "content": text + extra}]
        else:
            msgs = [{"role": "system", "content": sp + extra}] + hist + [{"role": "user", "content": text}]
        used, details, after = [], [], None
        for _round in range(5):
            content, calls = self._call(brain, msgs, sch, mode)
            if not calls and mode == "voice" and looks_broken(content) and not getattr(self, "_streamed", 0) and _round == 0:
                log.info("garbled reply from %s, retrying with the %s model", getattr(self, "last_model", "?"), "fast" if self._hard else "big")
                self._hard = not self._hard
                continue
            if not calls:
                say = (content or "").strip() or ("Done." if used else "Say that again?")
                if mode == "voice":
                    say = re.sub(r"```.*?```", "", say, flags=re.S)
                    say = re.sub(r"[*_#`>|]", "", say)
                    say = re.sub(r"https?://\S+", "", say).strip()
                return {"say": say, "detail": "\n\n".join(details), "after": after, "brain": brain, "tools": used}
            msgs.append({"role": "assistant", "content": content or "", "tool_calls": [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["args"])}} for c in calls]})
            for c in calls[:4]:
                name = c["name"]; used.append(name)
                if self.status_cb:
                    try: self.status_cb(chat_id, name)
                    except Exception: pass
                fn = funcs.get(name)
                if not fn:
                    res = f"No tool called {name}."
                else:
                    try:
                        res = fn(**(c["args"] or {}))
                    except TypeError:
                        try: res = fn()
                        except Exception as e: res = f"Tool error: {e}"
                    except Exception as e:
                        log.exception("tool %s", name); res = f"Tool error: {e}"
                if isinstance(res, dict) and res.get("confirm"):
                    if res.get("detail"):
                        details.append(res["detail"])
                    return {"say": res.get("say") or "Shall I proceed?", "confirm": res["confirm"], "confirm_desc": res.get("confirm_desc", name),
                            "detail": "\n\n".join(details), "brain": brain, "tools": used}
                if isinstance(res, dict):
                    if res.get("after"): after = res["after"]
                    if res.get("detail"): details.append(res["detail"])
                    out = res.get("tool_output") or (res.get("say", "") + ("\n" + res["detail"] if res.get("detail") else ""))
                else:
                    out = str(res)
                msgs.append({"role": "tool", "tool_call_id": c["id"], "name": name, "content": out[:9000]})
        return {"say": "That took a lot of steps, here's what I got so far.", "detail": "\n\n".join(details), "brain": brain, "tools": used}

    # ---------------------------------------------------------------- confirmations (chat window + phone)
    def set_pending(self, res, chat_id):
        self.pending = {"id": secrets.token_hex(4), "fn": res["confirm"], "desc": res.get("confirm_desc", ""), "at": time.time(), "chat": chat_id}
        return self.pending["id"]

    def resolve(self, pid, yes):
        p = self.pending
        if not p or (pid and pid != p["id"]):
            return {"say": "There's nothing waiting for a yes anymore."}
        self.pending = None
        if time.time() - p["at"] > 120:
            actlog.write("DECLINED", p["desc"], None, "too late")
            return {"say": "That took too long so I didn't do it. Ask again."}
        if not yes:
            actlog.write("DECLINED", p["desc"], None, "User said no")
            return {"say": "Understood. I've left it alone."}
        actlog.write("CONFIRMED", p["desc"], None, "User said yes")
        r = p["fn"]()
        return {"say": r} if isinstance(r, str) else (r or {"say": "Done."})


# -------------------------------------------------------------------- chat history (local files)
def _cp(cid):
    os.makedirs(CHATS, exist_ok=True)
    return os.path.join(CHATS, re.sub(r"[^\w-]", "", cid) + ".json")


def list_chats():
    os.makedirs(CHATS, exist_ok=True)
    out = []
    for f in os.listdir(CHATS):
        if f.endswith(".json"):
            try:
                d = json.load(open(os.path.join(CHATS, f), encoding="utf-8"))
                out.append({"id": d["id"], "title": d.get("title") or "New chat", "updated": d.get("updated", "")})
            except Exception:
                pass
    return sorted(out, key=lambda x: x["updated"], reverse=True)


def load_chat(cid):
    try:
        return json.load(open(_cp(cid), encoding="utf-8"))
    except Exception:
        return {"id": cid, "title": "New chat", "messages": [], "updated": ""}


def save_chat(c):
    c["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    if (not c.get("title") or c["title"] == "New chat") and c["messages"]:
        first = next((m["content"] for m in c["messages"] if m["role"] == "user"), "New chat")
        c["title"] = (first[:40] + "…") if len(first) > 40 else first
    with open(_cp(c["id"]), "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1)


def delete_chat(cid):
    try: os.remove(_cp(cid))
    except Exception: pass
    return True


def new_id():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]


# -------------------------------------------------------------------- one chat turn (desktop window + phone)
YES_WORDS = {"yes", "yeah", "yep", "yup", "y", "do it", "go ahead", "yes do it", "confirm", "sure", "ok", "okay", "run it", "send it"}
NO_WORDS = {"no", "nah", "nope", "n", "cancel", "don't", "dont", "stop", "never mind", "nevermind"}


def _fmt(res, engine, chat_id):
    out = {"reply": res.get("say", ""), "detail": res.get("detail", ""), "needs_confirm": False, "confirm_id": "",
           "brain": brain_label(res.get("brain")) if res.get("brain") else "", "tools": res.get("tools", []), "note": res.get("note", "")}
    if res.get("confirm"):
        out.update(needs_confirm=True, confirm_id=engine.set_pending(res, chat_id), confirm_what=res.get("confirm_desc", ""))
    if res.get("after"):
        def go():
            time.sleep(0.4)
            try: res["after"]()
            except Exception: log.exception("after")
        threading.Thread(target=go, daemon=True).start()
    return out


def chat_turn(vex, chat_id, text, source="desktop"):
    from .brain import norm, KILL
    engine = vex.engine
    chat_id = chat_id or new_id()
    c = load_chat(chat_id)
    t = norm(text).strip(" ,.!?")
    name = config.get("assistant_name").lower()
    c["messages"].append({"role": "user", "content": text, "ts": time.time()})
    if t in KILL or t in {f"{name} stop", f"stop {name}"} or t in set(config.get("kill_phrases") or []):
        vex.cancel_all(source); engine.pending = None
        out = {"reply": "Stopped. Everything's cancelled.", "detail": "", "needs_confirm": False, "confirm_id": ""}
    elif engine.pending and (t in YES_WORDS or t in NO_WORDS) and source == "desktop":
        out = _fmt(engine.resolve(engine.pending["id"], t in YES_WORDS), engine, chat_id)
    else:
        res = None
        if engine.pending:
            actlog.write("DECLINED", engine.pending["desc"], None, "new message instead of yes"); engine.pending = None
        if len(t.split()) <= 9 and "?" not in text and "\n" not in text:
            try:
                res = vex.brain._rules(t)  # instant PC commands (open steam, volume up, ...)
            except Exception:
                res = None
            if isinstance(res, str):
                res = {"say": res}
        if not res:
            hist = [{"role": m["role"], "content": m["content"] + (("\n\n" + m["detail"]) if m.get("detail") else "")}
                    for m in c["messages"][:-1] if m["role"] in ("user", "assistant")]
            res = engine.ask(text, hist, "chat", chat_id)
        out = _fmt(res, engine, chat_id)
    c["messages"].append({"role": "assistant", "content": out["reply"], "detail": out.get("detail", ""), "ts": time.time(),
                          "brain": out.get("brain", ""), "tools": out.get("tools", [])})
    save_chat(c)
    out["chat_id"] = chat_id
    out["title"] = c.get("title")
    return out


def chat_confirm(vex, pid, yes):
    engine = vex.engine
    p = engine.pending
    chat_id = p["chat"] if p else None
    out = _fmt(engine.resolve(pid, yes), engine, chat_id)
    if chat_id:
        c = load_chat(chat_id)
        c["messages"].append({"role": "user", "content": "Yes" if yes else "No", "ts": time.time()})
        c["messages"].append({"role": "assistant", "content": out["reply"], "detail": out.get("detail", ""), "ts": time.time()})
        save_chat(c)
    out["chat_id"] = chat_id
    return out
