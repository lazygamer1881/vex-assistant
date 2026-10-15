"""Vex 3.2 AI agent connections. Local Ollama is the default; cloud agents only run with a key the user pastes in (stored with DPAPI)."""
import re, json, time, logging, urllib.request, urllib.error
from . import config, vault

log = logging.getLogger("vex.conn")
# name: label, kind, base url, default model, needs key
AGENTS = {
    "local":      ("Local · Ollama", "ollama", "", "", False),
    "openai":     ("OpenAI", "openai", "https://api.openai.com/v1", "gpt-4o-mini", True),
    "groq":       ("Groq", "openai", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", True),
    "openrouter": ("OpenRouter", "openai", "https://openrouter.ai/api/v1", "openrouter/auto", True),
    "lmstudio":   ("LM Studio (local)", "openai", "http://127.0.0.1:1234/v1", "local-model", False),
    "gemini":     ("Google Gemini", "openai", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash", True),
    "anthropic":  ("Anthropic Claude", "anthropic", "https://api.anthropic.com/v1", "claude-haiku-4-5", True),
    "webhook":    ("Custom agent (webhook / MCP bridge)", "webhook", "", "", False),
}
ALIASES = {"chatgpt": "openai", "gpt": "openai", "open ai": "openai", "claude": "anthropic", "gemini": "gemini", "google": "gemini",
           "groq": "groq", "grok": "groq", "open router": "openrouter", "openrouter": "openrouter", "lm studio": "lmstudio",
           "local": "local", "ollama": "local", "webhook": "webhook", "agent": "webhook", "my agent": "webhook", "custom agent": "webhook"}


def key(name):
    return vault.get(name + "_key") or ""


def configured(name):
    if name == "local": return True
    if name == "lmstudio": return bool(config.get("lmstudio_enabled"))
    if name == "webhook": return bool(config.get("agent_webhook_url"))
    return bool(key(name))


def listing():
    out = []
    for n, (label, kind, base, model, needs) in AGENTS.items():
        out.append({"id": n, "label": label, "kind": kind, "needs_key": needs, "configured": configured(n), "key_set": bool(key(n)) if needs else False,
                    "model": config.get(n + "_model") or model, "base": (config.get("lmstudio_url") or base) if n == "lmstudio" else base,
                    "url": config.get("agent_webhook_url") if n == "webhook" else ""})
    return {"agents": out, "brain": config.get("brain") or "auto", "hard": config.get("hard_provider") or "",
            "vault_ok": _vault_ok()}


def _vault_ok():
    try: return vault.selftest()
    except Exception: return False


def save(name, fields):
    if name not in AGENTS: return {"ok": False, "msg": "Unknown agent"}
    f = dict(fields or {})
    if f.get("key"): vault.put(name + "_key", f["key"].strip())
    if f.get("clear"): vault.put(name + "_key", "")
    if "model" in f and f["model"].strip(): config.save({name + "_model": f["model"].strip()[:80]})
    if name == "lmstudio":
        config.save({"lmstudio_enabled": bool(f.get("enabled", True)) and not f.get("clear"), "lmstudio_url": (f.get("base") or AGENTS["lmstudio"][2]).strip()})
    if name == "webhook":
        u = "" if f.get("clear") else (f.get("url") or "").strip()
        if u and not re.match(r"^https?://", u): return {"ok": False, "msg": "URL must start with http:// or https://"}
        config.save({"agent_webhook_url": u})
        if f.get("key"): vault.put("webhook_key", f["key"].strip())
    return {"ok": True, "msg": "Cleared" if f.get("clear") else "Saved (key encrypted with Windows DPAPI)"}


def set_route(brain, hard):
    ok = set(AGENTS) | {"auto"}
    upd = {}
    if brain in ok: upd["brain"] = brain
    if hard in ok or hard == "": upd["hard_provider"] = "" if hard in ("auto", "local") else hard
    config.save(upd)
    return listing()


HARD = re.compile(r"\b(explain|why|how does|analy[sz]e|compare|write (?:a|me)|code|script|debug|essay|plan|strategy|calculate|prove|summari[sz]e)\b", re.I)


def is_hard(text):
    return len(text) > 140 or bool(HARD.search(text))


def _post(url, body, headers, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:200].decode('utf8', 'replace')}")


def ask_webhook(text):
    u = config.get("agent_webhook_url")
    if not u: raise RuntimeError("No custom agent URL set (Connections tab).")
    h = {"Authorization": "Bearer " + vault.get("webhook_key")} if vault.get("webhook_key") else {}
    r = _post(u, {"input": text, "source": "vex", "user": config.get("user_name")}, h, timeout=60)
    return str(r.get("reply") or r.get("output") or r.get("text") or r.get("content") or json.dumps(r)[:400])


def test(name):
    try:
        if name == "webhook":
            return {"ok": True, "msg": "Reply: " + ask_webhook("ping")[:120]}
        if name == "local":
            with urllib.request.urlopen(config.get("ollama_url").rstrip("/") + "/api/tags", timeout=5) as r:
                n = len(json.loads(r.read()).get("models", []))
            return {"ok": True, "msg": f"Ollama running, {n} models"}
        from . import chat
        e = chat.Engine()
        c, _ = e._call(name, [{"role": "user", "content": "Reply with just: online"}], None, "voice")
        return {"ok": True, "msg": "Reply: " + (c or "")[:80]}
    except Exception as ex:
        return {"ok": False, "msg": str(ex)[:200]}


def resolve_alias(s):
    s = (s or "").lower().strip()
    return ALIASES.get(s) or (s if s in AGENTS else None)
