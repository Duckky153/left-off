#!/usr/bin/env python3
"""The second check: TypeSafe's Jev answers fixed questions (questions.json) by picking from options or giving a
yes-or-no probability. It writes nothing. Every request is sent twice, the second time with every list of options
reversed; an answer counts only when both reads agree and pass the threshold, and a yes-or-no uses the less
favorable of the two reads. On a waiting question it picks the line that answers it and judges whether the record answers
it, so it decides which questions reach the writer; everywhere else it can only add a hold. Unsure means hold.

    python3 jev_check.py router --set practice      # read every waiting message that reaches step 4
    python3 jev_check.py drafts --set practice      # check every draft

The key is read only from TYPESAFE_API_KEY and never printed or saved. Every paid attempt is logged in
cache/spend.jsonl (never published). The cap is checked before every run and every call.
"""
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

import followup_core as core
import views

HERE = pathlib.Path(__file__).resolve().parent
URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"
PRICE_PER_TOKEN = 0.042 / 1_000_000   # $0.042 per million input tokens; output is free
WORST_TOKENS = 64_000                 # the most the service accepts in one request
CAP = 0.50                            # this build's cap, approved with the plan
LEDGER = HERE / "cache" / "spend.jsonl"
PRIVATE = HERE / "local" / "private-paths.json"


class Refused(RuntimeError):
    pass


# ------------------------------------------------------------------ requests

def facts_state(view):
    rows = views.numbered(view)
    return rows, "\n".join(f"{fid}| {t}" for fid, t in rows)


def choice(spec, options, reverse):
    crit = {o: None for o in options}
    if reverse:
        crit = dict(reversed(list(crit.items())))
    return {"type": "choice", "instructions": spec["instructions"], "criteria": crit}


def router_request(rec, view, qfile, reverse=False):
    rows, text = facts_state(view)
    R = qfile["router"]
    qs = {k: {"type": "noul", "instructions": R[k]["instructions"]} for k in ("about_money", "asks_to_stop", "complaint", "instructs_writer", "answered")}
    qs["answer_line"] = choice(R["answer_line"], [fid for fid, _ in rows], reverse)
    if reverse:
        qs = dict(reversed(list(qs.items())))
    return {"model": MODEL, "state": {"shopper_message": rec["message"]["text"], "facts": text}, "questions": qs}, dict(rows)


def sentences_of(draft):
    import re
    return [s for s in re.split(r"(?<=[.?!])\s+", draft.strip()) if s]


def draft_request(rec, view, draft, qfile, reverse=False):
    rows, text = facts_state(view)
    if view.get("question"):
        text += f"\nQUESTION| {view['question']}"
    sents = sentences_of(draft)
    D = qfile["draft"]
    qs = {}
    for n in range(1, len(sents) + 1):
        qs[f"D{n}_grounded"] = {"type": "noul", "instructions": D["grounded"]["instructions"].format(n=n)}
    qs["support"] = choice(D["support"], [fid for fid, _ in rows], reverse)
    for k in ("money", "pressure", "promise"):
        qs[k] = {"type": "noul", "instructions": D[k]["instructions"]}
    if view.get("answer"):
        qs["answers"] = {"type": "noul", "instructions": D["answers"]["instructions"]}
    if reverse:
        qs = dict(reversed(list(qs.items())))
    state = {"facts": text, "draft": "\n".join(f"D{i}| {s}" for i, s in enumerate(sents, 1)), "next_step": view["next_step"],
             "first_name": "{first_name}"}
    return {"model": MODEL, "state": state, "questions": qs}, dict(rows)


def state_hash(state):
    """A fingerprint of exactly what a read was asked, so a saved read counts only for the same facts and wording."""
    import hashlib
    return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def router_state(rec, view, qfile):
    return state_hash(router_request(rec, view, qfile)[0]["state"])


def draft_state(rec, view, draft, qfile):
    return state_hash(draft_request(rec, view, draft, qfile)[0]["state"])


def check_reply(reply, questions):
    if reply.get("model") != MODEL:
        return f"model is {reply.get('model')!r}, not {MODEL}"
    usage = reply.get("usage") or {}
    if not isinstance(usage.get("input_tokens"), int) or usage["input_tokens"] <= 0:
        return "usage.input_tokens missing"
    answers = reply.get("answers")
    if not isinstance(answers, dict):
        return "no answers"
    for qid, q in questions.items():
        a = answers.get(qid)
        if not isinstance(a, dict):
            return f"{qid} missing"
        if q["type"] == "noul":
            p = a.get("noul")
            if not isinstance(p, (int, float)) or not 0 <= p <= 1:
                return f"{qid} is not a number between 0 and 1"
        elif a.get("choice") not in q["criteria"]:
            return f"{qid} answer {a.get('choice')!r} is not an allowed option"
    return None


# ------------------------------------------------------------------ the two reads

def noul_pair(a, b, qid):
    x, y = a.get(qid, {}).get("noul"), b.get(qid, {}).get("noul")
    return (x, y) if x is not None and y is not None else None


def pick_pair(a, b, qid, threshold):
    x, y = a.get(qid) or {}, b.get(qid) or {}
    cx, cy = x.get("choice"), y.get("choice")
    px = (x.get("probabilities") or {}).get(cx, x.get("confidence", 0))
    py = (y.get("probabilities") or {}).get(cy, y.get("confidence", 0))
    return cx if cx == cy and cx is not None and min(px, py) >= threshold else None


def label_of(rows, fid):
    return rows.get(fid, "").split(":", 1)[0] if fid else None


ROUTER_READS = (("asks_to_stop", "asks_to_stop_max", None), ("instructs_writer", "instructs_writer_max", "instructions"),
                ("complaint", "complaint_max", "complaint"), ("about_money", "about_money_max", "money"))


def reasons_from(log, th):
    """From the reads' yes-or-no pairs: a request to stop comes first; otherwise, of the readings over their limits, the strongest
    sets the reason (a money question that also sounds a little like orders to the AI is a money question)."""
    out, flagged = {}, []
    for qid, limit_key, result in ROUTER_READS:
        pair = log.get(qid)
        if pair is None:
            out["not_checked"] = True
            continue
        if max(pair) > th[limit_key]:
            if qid == "asks_to_stop":
                out["asks_to_stop"] = True
            else:
                flagged.append((max(pair), result))
    if flagged:
        out["reason"] = max(flagged)[1]
    return out


def read_router(a, b, rows, th):
    log = {qid: noul_pair(a, b, qid) for qid, _, _ in ROUTER_READS}
    out = reasons_from(log, th)
    ans = noul_pair(a, b, "answered")
    log["answered"] = ans
    out["answered"] = ans is not None and min(ans) >= th["answered_min"]
    fid = pick_pair(a, b, "answer_line", th["answer_line_min"])
    log["answer_line"] = [a.get("answer_line", {}).get("choice"), b.get("answer_line", {}).get("choice")]
    out["answer_line"] = label_of(rows, fid)
    if out.get("answer_line") is None:
        out["answered"] = False
    return out, log


def read_draft(a, b, rows, th, n_sentences, has_question):
    fails, log = [], {}
    for n in range(1, n_sentences + 1):
        pair = noul_pair(a, b, f"D{n}_grounded")
        log[f"D{n}_grounded"] = pair
        if pair is None or min(pair) < th["grounded_min"]:
            fails.append(("not in the record (second check)", [f"sentence {n}"]))
    for qid, limit, name in (("money", th["money_max"], "money (second check)"), ("pressure", th["pressure_max"], "pressure (second check)"),
                             ("promise", th["promise_max"], "promise (second check)")):
        pair = noul_pair(a, b, qid)
        log[qid] = pair
        if pair is None or max(pair) > limit:
            fails.append((name, []))
    if has_question:
        pair = noul_pair(a, b, "answers")
        log["answers"] = pair
        if pair is None or min(pair) < th["answers_min"]:
            fails.append(("didn't answer (second check)", []))
    support = label_of(rows, pick_pair(a, b, "support", th["support_min"]))
    log["support"] = [a.get("support", {}).get("choice"), b.get("support", {}).get("choice")]
    return {"fails": fails, "support": support}, log


# ------------------------------------------------------------------ spending

def tokens_in(path):
    path = pathlib.Path(path)
    if not path.exists():
        return 0
    total = 0
    for row in path.read_text().splitlines():
        if row.strip():
            try:
                total += int(json.loads(row).get("input_tokens") or 0)
            except ValueError:
                continue
    return total


def room_left():
    if not PRIVATE.exists():
        raise Refused("the account-wide limit can't be checked without local/private-paths.json; no call made")
    private = json.loads(PRIVATE.read_text())
    others = sum(tokens_in(p) for p in private["other_spend_logs"]) * PRICE_PER_TOKEN
    mine = tokens_in(LEDGER) * PRICE_PER_TOKEN
    return min(CAP - mine, private["account_limit"] - others - mine), mine


def log_attempt(tag, rid, tokens, outcome):
    LEDGER.parent.mkdir(exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps({"t": round(time.time()), "tag": tag, "id": rid, "outcome": outcome, "model": MODEL,
                            "input_tokens": WORST_TOKENS if tokens is None else tokens, "estimated": tokens is None}) + "\n")


def post(body, key):
    req = urllib.request.Request(URL, data=body, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                                                          "User-Agent": "research-prototype/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def ask(body_obj, key, tag, rid):
    body = json.dumps(body_obj).encode()
    delay, attempts = 2.0, 0
    while True:
        room, _ = room_left()
        if room < WORST_TOKENS * PRICE_PER_TOKEN:
            raise Refused(f"only ${room:.4f} left under the cap; stopped before a call that could cross it")
        attempts += 1
        try:
            reply = post(body, key)
            tokens = (reply.get("usage") or {}).get("input_tokens")
            log_attempt(tag, rid, tokens if isinstance(tokens, int) and tokens > 0 else None, "ok")
            return reply
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504, 529) and attempts < 5:
                log_attempt(tag, rid, None, f"retry {e.code}")
                time.sleep(delay)
                delay *= 2
                continue
            log_attempt(tag, rid, None, f"failed {e.code}")
            raise Refused(f"{rid}: the service said {e.code}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempts < 5:
                log_attempt(tag, rid, None, "retry network")
                time.sleep(delay)
                delay *= 2
                continue
            log_attempt(tag, rid, None, "failed network")
            raise Refused(f"{rid}: network: {e}")


# ------------------------------------------------------------------ the passes

class Capture:
    """Runs the rules and captures what the second check would be asked, without calling it."""

    def __init__(self, router=None, drafts=None):
        self.router_saved, self.drafts = router or {}, drafts or {}
        self.router_calls, self.draft_calls = {}, {}

    def router(self, rec, view):
        if rec["id"] in self.router_saved:
            return self.router_saved[rec["id"]]
        self.router_calls[rec["id"]] = (rec, view)
        return {"answered": True, "answer_line": None}

    def draft(self, rec, view):
        d = self.drafts.get(rec["id"])
        return d["text"] if d else None

    def check(self, rec, view, draft):
        self.draft_calls[rec["id"]] = (rec, view, draft)
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


def run(stage, set_name, only=None):
    import leftoff
    s = json.loads((HERE / "settings.json").read_text())
    if set_name == "scored" and not s.get("drafts_suffix", {}).get("scored"):
        check_scored_lock()
    qfile = json.loads((HERE / "questions.json").read_text())
    th = qfile["thresholds"]
    out_path = HERE / "checks" / f"{set_name}-{qfile['version']}.json"
    saved = json.loads(out_path.read_text()) if out_path.exists() else {"questions": qfile["version"], "checks": {}, "log": {}}
    recs = leftoff.records(set_name)
    router = {k: v["router"] for k, v in saved["checks"].items() if "router" in v}
    drafts = {}
    if stage == "drafts":
        drafts = json.loads((HERE / "drafts" / f"{set_name}-{s['prompt']}{s.get('drafts_suffix', {}).get(set_name, '')}.json").read_text())["drafts"]
    cap = Capture(router if stage == "drafts" else {}, drafts)
    core.decide(recs, cap)
    calls = cap.router_calls if stage == "router" else cap.draft_calls
    if only:
        calls = {k: v for k, v in calls.items() if k in only}
    if stage == "router":  # read again whenever what it would be asked changed (the facts, the wording, the message)
        calls = {k: v for k, v in calls.items() if saved["checks"].get(k, {}).get("router", {}).get("state") != router_state(*v, qfile)}
    else:  # a draft is checked again whenever its text or its facts changed
        calls = {k: v for k, v in calls.items() if saved["checks"].get(k, {}).get("draft", {}).get("state") != draft_state(*v, qfile)}
    n = 2 * len(calls)
    room, spent = room_left()
    if n * WORST_TOKENS * PRICE_PER_TOKEN > room:
        raise Refused(f"worst case ${n * WORST_TOKENS * PRICE_PER_TOKEN:.4f} for {n} calls is more than the ${room:.4f} left under the cap")
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise Refused("TYPESAFE_API_KEY is not set")
    tag = f"{set_name}:{stage}:{qfile['version']}:{s['prompt']}"
    for rid, args in sorted(calls.items()):
        replies = []
        for rev in (False, True):
            body, rows = (router_request(*args, qfile, reverse=rev) if stage == "router" else draft_request(*args, qfile, reverse=rev))
            reply = ask(body, key, tag, rid)
            bad = check_reply(reply, body["questions"])
            replies.append(None if bad else reply["answers"])
        entry = saved["checks"].setdefault(rid, {})
        if None in replies:
            entry["router" if stage == "router" else "draft"] = {"not_checked": True}
            continue
        if stage == "router":
            entry["router"], saved["log"][f"{rid}:router"] = read_router(replies[0], replies[1], rows, th)
            entry["router"]["state"] = router_state(*args, qfile)
        else:
            entry["draft"], saved["log"][f"{rid}:draft"] = read_draft(replies[0], replies[1], rows, th,
                                                                      len(sentences_of(args[2])), bool(args[1].get("answer")))
            entry["draft"]["text"] = args[2]
            entry["draft"]["state"] = draft_state(*args, qfile)
        print(f"{rid}: {stage} checked", flush=True)
    _, spent = room_left()
    saved.setdefault("runs", []).append({"stage": stage, "calls": n, "spent_so_far_dollars": round(spent, 5), "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(saved, indent=1) + "\n")
    print(f"wrote {out_path.relative_to(HERE)}: {n} calls; build spend ${spent:.4f}")


def rederive(set_name, from_version):
    """Re-decide saved message reads under the current limits, with no new calls. Only for a questions version whose wording
    matches the one read (here lo-q7, which changed limits and how a reason is chosen, not any question)."""
    qfile = json.loads((HERE / "questions.json").read_text())
    src = json.loads((HERE / "checks" / f"{set_name}-{from_version}.json").read_text())
    out = {"questions": qfile["version"], "rederived_from": from_version, "checks": {}, "log": src["log"], "runs": src.get("runs", [])}
    for rid, entry in src["checks"].items():
        new = dict(entry)
        r = entry.get("router")
        if r and not r.get("not_checked") and f"{rid}:router" in src["log"]:
            log = src["log"][f"{rid}:router"]
            new["router"] = {**reasons_from(log, qfile["thresholds"]), "answered": r["answered"], "answer_line": r.get("answer_line")}
        out["checks"][rid] = new
    path = HERE / "checks" / f"{set_name}-{qfile['version']}.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {path.relative_to(HERE)} from {from_version}: no calls")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "rederive":
        rederive(args[args.index("--set") + 1], args[args.index("--from") + 1])
        sys.exit(0)
    stage = args[0] if args else "router"
    set_name = args[args.index("--set") + 1] if "--set" in args else "practice"
    try:
        only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
        run("drafts" if stage == "drafts" else "router", set_name, only)
    except Refused as e:
        print(f"Refused: {e}", file=sys.stderr)
        sys.exit(1)
