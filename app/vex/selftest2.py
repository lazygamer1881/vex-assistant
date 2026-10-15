"""Vex 2.0 headless self test (no window, no mic; PC tools in dry-run). Usage: python -m vex.selftest2"""
import os, sys, json, time, zipfile, traceback
from . import config, tools, assist, chat


def run():
    config.load()
    tools.DRY_RUN = True
    R = {}
    def step(name, fn):
        t0 = time.time()
        try:
            r = fn(); ok = True
        except Exception as e:
            r = f"{type(e).__name__}: {e} {traceback.format_exc()[-400:]}"; ok = False
        R[name] = {"ok": ok, "sec": round(time.time() - t0, 1), "result": str(r)[:500]}
        print(("OK  " if ok else "FAIL"), name, f"({R[name]['sec']}s):", str(r)[:300].replace("\n", " | "), flush=True)
    from .core import ensure_ollama
    step("ollama", lambda: (ensure_ollama(), "up")[1])
    step("web_search", lambda: (lambda r: r if r else (_ for _ in ()).throw(RuntimeError("no results")))(assist.web_search("Python programming language")[:2]))
    step("read_webpage", lambda: assist.read_webpage("https://example.com")[:120])
    step("weather", lambda: assist.weather())
    def mem():
        assist.remember("SELFTEST favorite color is purple")
        ok = any("SELFTEST" in m["text"] for m in assist.memories())
        assist.forget("SELFTEST")
        assert ok and not any("SELFTEST" in m["text"] for m in assist.memories())
        return "add + forget ok"
    step("memory", mem)
    def rem():
        got = []
        assist.notify_cb = lambda t, x: got.append(x)
        import threading
        threading.Thread(target=assist.reminder_loop, daemon=True).start()
        msg = assist.set_reminder("SELFTEST stretch", "in 3 seconds")
        for _ in range(30):
            if got: break
            time.sleep(0.5)
        assert got, "reminder never fired"
        return msg + " -> fired: " + got[0]
    step("reminder", rem)
    def files():
        d = os.path.join(assist.DATA, "selftest"); os.makedirs(d, exist_ok=True)
        t = os.path.join(d, "notes.txt"); open(t, "w").write("The mitochondria is the powerhouse of the cell. Homework due Friday.")
        x = os.path.join(d, "essay.docx")
        with zipfile.ZipFile(x, "w") as z:
            z.writestr("word/document.xml", '<w:document><w:body><w:p><w:r><w:t>Volcanoes form at plate boundaries.</w:t></w:r></w:p></w:body></w:document>')
        a, b = assist.read_file(t), assist.read_file(x)
        assert "mitochondria" in a and "Volcanoes" in b
        try:
            import pypdf; pdf = "pypdf ok"
        except Exception:
            pdf = "pypdf MISSING"
        return "txt + docx ok, " + pdf
    step("file_read", files)
    e = chat.Engine()
    step("local_chat", lambda: (lambda r: r["say"] if r.get("brain") == "local" and "error" not in r else (_ for _ in ()).throw(RuntimeError(str(r))))(chat.Engine()._ask("local", "What is 7 times 8? Answer in one short sentence.", [], "chat", None)))
    step("local_tool_weather", lambda: (lambda r: f"tools={r.get('tools')} say={r['say']}")(e._ask("local", "What's the weather like right now?", [], "chat", None)))
    step("local_tool_search", lambda: (lambda r: f"tools={r.get('tools')} say={r['say'][:200]}")(e._ask("local", "Search the web: who won the 2026 FIFA World Cup?", [], "chat", None)))
    def fsum():
        p = os.path.join(assist.DATA, "selftest", "notes.txt")
        r = e._ask("local", f"Summarize the file {p} in one sentence.", [], "chat", None)
        return f"tools={r.get('tools')} say={r['say'][:200]}"
    step("local_file_summary", fsum)
    step("local_tool_memory", lambda: (lambda r: (assist.forget("pizza"), f"tools={r.get('tools')} say={r['say']}")[1])(e._ask("local", "Remember that my favorite food is pizza.", [], "chat", None)))
    step("python_confirm", lambda: (lambda r: "asks first" if r.get("confirm") else (_ for _ in ()).throw(RuntimeError("ran without asking")))(assist.run_python("print(6*7)")))
    step("python_run", lambda: assist.run_python("print(6*7)")["confirm"]()["detail"])
    step("brain_label", lambda: chat.brain_label())
    out = os.path.join(config.LOG_DIR, "selftest2.json")
    os.makedirs(config.LOG_DIR, exist_ok=True)
    json.dump(R, open(out, "w"), indent=1)
    print("PASSED", sum(r["ok"] for r in R.values()), "of", len(R))


if __name__ == "__main__":
    run()
