#!/usr/bin/env python3
"""The writer: an open model running on this computer through Ollama (127.0.0.1 only). Nothing leaves the machine.

    python3 write.py --set practice --prompt v1      # draft for every practice shopper who reaches the draft step

It drafts only for shoppers the rules and the first read let through, saves every draft with the exact text the model
was given, and writes drafts/<set>-<prompt>.json and runs/<set>-<prompt>-<n>.json. A prompt file is never changed after
its first run: a new version is a new file.
"""
import hashlib
import json
import pathlib
import sys
import time
import urllib.request

import followup_core as core
import views

HERE = pathlib.Path(__file__).resolve().parent
OLLAMA = "http://127.0.0.1:11434"


def settings():
    return json.loads((HERE / "settings.json").read_text())


def call(model, system, user, opts):
    body = {"model": model, "stream": False, "think": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": opts}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.loads(r.read())
    return out, round(time.time() - t, 2)


def model_digest(model):
    req = urllib.request.Request(f"{OLLAMA}/api/tags")
    with urllib.request.urlopen(req, timeout=30) as r:
        tags = json.loads(r.read())["models"]
    return next((m["digest"] for m in tags if m["name"] == model or m["model"] == model), None)


def clean(text):
    t = " ".join((text or "").strip().split())
    return t.strip('"').strip()


class Collect:
    """Runs the rules with the saved first-read answers, and collects the views of shoppers who reach the draft step."""

    def __init__(self, router):
        self.router_answers, self.views = router, {}

    def router(self, rec, view):
        return self.router_answers.get(rec["id"], {}).get("router")

    def draft(self, rec, view):
        self.views[rec["id"]] = view
        return None

    def check(self, rec, view, draft):
        return {}


def check_scored_lock():
    """The scored run refuses to start unless every file in lock.json's before_scored_run matches and is committed."""
    import hashlib
    import subprocess
    lock = json.loads((HERE / "lock.json").read_text()).get("before_scored_run")
    if not lock:
        raise SystemExit("Refused: no before_scored_run lock yet")
    moved = [f for f, h in lock["fingerprints"].items() if hashlib.sha256((HERE / f).read_bytes()).hexdigest() != h]
    if moved:
        raise SystemExit(f"Refused: changed since the lock: {moved}")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *lock["fingerprints"]], cwd=HERE, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"Refused: commit these before the scored run:\n{dirty}")
    return lock


def run(set_name, prompt_version, model=None, tag=None, prompt_file=None, router_override=None):
    s = settings()
    if set_name == "scored" and not tag:
        lock = check_scored_lock()
        if not tag and (HERE / "drafts" / f"scored-{prompt_version}.json").exists():
            raise SystemExit("Refused: the scored set has already been drafted once with this prompt")
    if set_name == "scored" and not tag:
        if model_digest(lock["model"]) != lock["model_digest"]:
            raise SystemExit("Refused: the local model is not the locked version")
    model = model or s["model"]
    prompt_path = pathlib.Path(prompt_file) if prompt_file else HERE / "prompts" / f"{prompt_version}.md"
    system = prompt_path.read_text()
    import leftoff
    recs = leftoff.records(set_name)
    cp = HERE / "checks" / f"{set_name}-{s['questions']}.json"
    router = json.loads(cp.read_text())["checks"] if cp.exists() else {}
    col = Collect(router_override if router_override is not None else router)
    picked, results = core.decide(recs, col)
    by_id = {r["id"]: r for r in results}
    opts = {k: s[k] for k in ("temperature", "seed", "num_predict", "num_ctx")}
    drafts, rows = {}, []
    for rid, view in sorted(col.views.items()):
        chan = by_id[rid].get("channel")
        user = "\n".join(views.writer_lines(view, chan, next_step=s.get("writer_sees_next_step", True)))
        out, secs = call(model, system, user, opts)
        text = clean(out["message"]["content"])
        drafts[rid] = {"text": text, "cut_off": out.get("done_reason") == "length"}
        rows.append({"id": rid, "user": user, "raw": out["message"]["content"], "text": text, "done_reason": out.get("done_reason"),
                     "prompt_tokens": out.get("prompt_eval_count"), "output_tokens": out.get("eval_count"), "seconds": secs})
        print(f"{rid}: {text}", flush=True)
    meta = {"set": set_name, "prompt": prompt_version, "prompt_sha256": hashlib.sha256(system.encode()).hexdigest(),
            "model": model, "model_digest": model_digest(model), "options": opts, "think": False, "drafts": len(drafts),
            "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (HERE / "runs").mkdir(exist_ok=True)
    (HERE / "drafts").mkdir(exist_ok=True)
    stem = f"{set_name}-{prompt_version}" + (f"-{tag}" if tag else "")
    n = 1
    while (HERE / "runs" / f"{stem}-{n}.json").exists():
        n += 1
    (HERE / "runs" / f"{stem}-{n}.json").write_text(json.dumps({"meta": meta, "rows": rows}, indent=1) + "\n")
    if not tag or tag == "code-only" or tag == s.get("drafts_suffix", {}).get(set_name, "").lstrip("-"):
        (HERE / "drafts" / f"{stem}.json").write_text(json.dumps({"meta": meta, "drafts": drafts}, indent=1) + "\n")
    print(f"wrote runs/{stem}-{n}.json: {len(drafts)} drafts with {model}")
    return drafts


def main(argv):
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    if "--code-only" in argv:  # drafts for the code-only comparison: routing by code's word lists and word match alone
        set_name = opt("--set", "practice")
        import leftoff
        override = {}
        for r in leftoff.records(set_name):
            if r.get("message"):
                v = views.build(r, "waiting", core.WORDING)
                override[r["id"]] = {"router": {"answered": core.code_answer_line(v, r["message"]["text"]) is not None, "answer_line": None}}
        run(set_name, opt("--prompt", settings()["prompt"]), tag="code-only", router_override=override)
        return
    run(opt("--set", "practice"), opt("--prompt", settings()["prompt"]), model=opt("--model"), tag=opt("--tag"),
        prompt_file=opt("--prompt-file"))


if __name__ == "__main__":
    main(sys.argv[1:])
