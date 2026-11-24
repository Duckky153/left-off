#!/usr/bin/env python3
"""Left Off, from the terminal.

    python3 leftoff.py run                      # decide the 40 from the saved drafts and checks (no key, no model)
    python3 leftoff.py run --source yardstick   # the same, with no AI at all (fixed sentences, code-only routing)
    python3 leftoff.py show S-1001              # one shopper: the queue, the rules, the facts the AI saw, the draft, its checks
    python3 leftoff.py export                   # write site/data/run.json for the page

Nothing here sends a message or makes a network call.
"""
import json
import re
import pathlib
import sys

import baseline
import followup_core as core
import views

HERE = pathlib.Path(__file__).resolve().parent


def records(set_name="scored"):
    f = {"scored": "shoppers.json", "practice": "practice.json", "fresh": "fresh.json", "fresh2": "fresh2.json", "fresh3": "fresh3.json", "fresh4": "fresh4.json", "fresh5": "fresh5.json", "fresh6": "fresh6.json"}[set_name]
    return json.loads((HERE / "sample" / f).read_text())["shoppers"]


class Saved:
    """The AI parts read from saved files: drafts/<set>-<prompt>.json and checks/<set>-<questions>.json."""
    name = "AI"

    def __init__(self, set_name="scored"):
        s = json.loads((HERE / "settings.json").read_text())
        suffix = s.get("drafts_suffix", {}).get(set_name, "")
        self.drafts = json.loads((HERE / "drafts" / f"{set_name}-{s['prompt']}{suffix}.json").read_text())["drafts"]
        cp = HERE / "checks" / f"{set_name}-{s['questions']}.json"
        saved = json.loads(cp.read_text()) if cp.exists() else {}
        self.checks, self.log = saved.get("checks", {}), saved.get("log", {})

    def router(self, rec, view):
        r = self.checks.get(rec["id"], {}).get("router")
        if r and "state" in r and r["state"] != self._jev().router_state(rec, view, self._q()):
            return {"not_checked": True}  # read on other facts or wording: it doesn't count
        return r

    def _jev(self):
        import jev_check
        return jev_check

    def _q(self):
        if not hasattr(self, "_qfile"):
            self._qfile = json.loads((HERE / "questions.json").read_text())
        return self._qfile

    def draft(self, rec, view):
        d = self.drafts.get(rec["id"])
        return d["text"] if d else None

    def check(self, rec, view, draft):
        c = self.checks.get(rec["id"], {}).get("draft")
        if c is None or ("text" in c and c["text"] != draft):
            return {"not_checked": True}
        if "state" in c and c["state"] != self._jev().draft_state(rec, view, draft, self._q()):
            return {"not_checked": True}  # checked against other facts or wording: it doesn't count
        return c


def source(name, set_name="scored"):
    if name not in ("ai", "saved", "yardstick"):
        raise SystemExit(f"No source {name!r}: use --source ai or --source yardstick")
    return baseline.Yardstick() if name == "yardstick" else Saved(set_name)


def line(r):
    label = core.WORDING["outcome_label"][r["outcome"]]
    W = core.WORDING
    why = ((W["read_as"].get(r["reason"]) if r.get("caught_by") == "second check" else None) or W["reasons"].get(r["reason"], "")) if r["reason"] else ""
    return f"{r['id']}  {core.WORDING['stop_name'][r['stop']]:<20} {r['kind']:<8} {label:<15} {why}"


def cmd_run(src, set_name):
    picked, results = core.decide(records(set_name), source(src, set_name))
    for r in results:
        print(line(r))
    c = core.counts(results)
    print(f"\n{c['shoppers']} shoppers: {c['ready']} ready, {c['person']} for a person, {c['do_not_contact']} do not contact")
    return results


def cmd_show(rid, src, set_name):
    recs = records(set_name)
    src_obj = source(src, set_name)
    picked, results = core.decide(recs, src_obj)
    r = next((x for x in results if x["id"] == rid), None)
    if not r:
        print(f"{rid} isn't in the queue." if any(x["id"] == rid for x in recs) else f"No shopper {rid}.")
        return 1
    print(line(r))
    if r.get("send_at_shown"):
        print(f"Channel: {r.get('channel')} · {r['send_at_shown']}")
    if r.get("view") and r.get("draft"):
        print("\nWhat the writing AI was given:")
        sees = json.loads((HERE / "settings.json").read_text()).get("writer_sees_next_step", True)
        for t in views.writer_lines(r["view"], r.get("channel", ""), next_step=sees):
            print("  " + t)
    elif r.get("view"):
        print("\nNo draft: the writing AI never saw this shopper.")
    if r.get("draft"):
        print("\nDraft:\n  " + r["draft"])
    log = getattr(src_obj, "log", {}).get(f"{rid}:draft", {})
    th = json.loads((HERE / "questions.json").read_text())["thresholds"]
    reads = {"money": ("money", "money_max", max), "pressure": ("pressure", "pressure_max", max), "promise": ("promise", "promise_max", max),
             "didn't answer": ("answers", "answers_min", min), "not in the record": ("D1_grounded", "grounded_min", min)}
    for f, w in r.get("failed", []):
        base = f.replace(" (second check)", "")
        if f.endswith("(second check)") and base in reads and log.get(reads[base][0]):
            qid, lim, pick = reads[base]
            print(f"  held by: {f}: read {pick(log[qid]):.2f}, limit {th[lim]:.2f}")
        else:
            print(f"  held by: {f}" + (f" ({', '.join(map(str, w))})" if w else ""))
    if r.get("message"):
        m = r["message"]
        print("\nMessage:\n  " + (m["text"] if m["channel"] == "text" else f"Subject: {m['subject']}\n  {m['body']}"))
    return 0


def ago(rec):
    clock = core.run_clock()
    if rec.get("message"):
        mins = int((clock - core.parse_time(rec["message"]["at"])).total_seconds() // 60)
        return f"Asked {mins} min ago" if mins < 60 else f"Asked {mins // 60}h ago"
    days = int((clock - core.parse_time(rec["last_activity_at"])).total_seconds() // 86400)
    return f"Quiet {days} days"


def stop_date(rec):
    st = rec["stop"]
    d = {"saved_car": (rec.get("car") or {}).get("saved_at"), "saved_search": (rec.get("search") or {}).get("saved_at"),
         "prequalified": (rec.get("prequal") or {}).get("done_at"), "purchase": (rec.get("purchase") or {}).get("started_at"),
         "trade_in_offer": (rec.get("offer") or {}).get("made_at"), "sell_offer": (rec.get("offer") or {}).get("made_at")}[st]
    return views.day(d) if d else None


def facts_line(rec):
    car = rec.get("car") or (rec.get("offer") or {}).get("car")
    bits = []
    if car:
        bits.append(f"{car['year']} {car['make']} {car['model']} {car['trim']}")
    elif rec.get("search"):
        bits.append(rec["search"]["desc"])
    if rec.get("city"):
        bits.append(f"{rec['city']}, {rec['state']}")
    return " · ".join(bits)


def usable(w):
    return isinstance(w, str) and w and not w[0].isdigit() and not w.startswith("sentence") and " sentences" not in w


def stopped_list(failed, W, log=None):
    """Each check that stopped a draft, with the words it marked: checks with marked words first; the second check's in plain words."""
    out, seen = [], set()
    for f, ws in failed:
        words = sorted({w for w in ws if usable(w)})
        key = W["check_plain"].get(f, f)
        if key in seen and not words:
            continue
        seen.add(key)
        if f.endswith(" (second check)"):
            out.append({"words": [], "by": "ai", "why": W["check_read"].get(f.replace(" (second check)", ""), key)})
        else:
            out.append({"words": words, "by": "code", "why": W["check_marked"].get(f, key) if words else key})
    return sorted(out, key=lambda x: 0 if x["words"] else 1)


def short_time(s):
    """'Tue, Nov 24, 10:00 am Mountain' -> 'Tue 10:00 am Mountain': the weekday is enough beside the sample date."""
    return re.sub(r"^(\w{3}), \w{3} \d{1,2}, ", r"\1 ", s) if s else s


def page_row(rec, r, log=None):
    stop, W = rec["stop"], core.WORDING
    steps = W["journey"][stop]
    reason = r["reason"]
    by_check = r.get("caught_by") == "second check"
    fails = [f for f, _ in r.get("failed", [])]
    row = {"id": rec["id"], "name": f"{rec['first_name']} {rec['last_initial']}.", "stop": W["stop_name"][stop],
           "ago": ago(rec), "facts": facts_line(rec), "journey": {"steps": steps, "at": 1 if stop == "purchase" else 0, "date": stop_date(rec)},
           "question": (rec.get("message") or {}).get("text"), "kind": r["kind"], "outcome": r["outcome"], "label": W["outcome_label"][r["outcome"]],
           "reason": (W["read_as"].get(reason) if by_check else W["reasons"].get(reason)) if reason else None,
           "list_reason": ((W["list_read_as"].get(reason) if by_check else None) or W["list_reason"].get(reason)) if reason else None,
           "reply_by": short_time(r.get("reply_by")),
           "channel": r.get("channel"), "send_at": r.get("send_at_shown"), "send_short": short_time(r.get("send_at_shown")),
           "title": W["panel_title"]["reply" if r["kind"] == "waiting" else "nudge"], "message": r.get("message"),
           "held_draft": r["draft"].replace("{first_name}", rec["first_name"]) if r["outcome"] == "person" and r.get("draft") else None,
           "stopped_because": sorted({W["check_plain"].get(f, f) for f in fails}),
           "stopped": stopped_list(r.get("failed", []), W, (log or {}).get(f"{rec['id']}:draft")),
           "caught": sorted({w for f, ws in r.get("failed", []) for w in ws if isinstance(w, str) and w and not w[0].isdigit()
                             and not w.startswith("sentence") and " sentences" not in w}),
           "strip": None,
           "record": [[W["record_label"].get(k, k.title()), v] for k, v in (r.get("view") or {}).get("lines", []) if k not in ("CAR", "YOUR CAR")],
           "used": W["record_label"].get((r.get("view") or {}).get("answer_label") or (r.get("view") or {}).get("true_label") or "", None) if r.get("draft") else None}
    if reason in ("california", "no_safe_time"):  # the strip says why; the status line stays short
        row["reason"] = W["list_reason"][reason]
    if r["outcome"] == "do_not_contact":
        row["strip"] = W["strip"].get(reason)
    elif r["outcome"] == "person" and not r.get("draft"):
        row["strip"] = W["strip"].get(reason)
        if reason == "money" and by_check:  # the second check's reading, said as a reading; a weak one says so
            pair = ((log or {}).get(f"{rec['id']}:router") or {}).get("about_money")
            row["strip"] = W["strip"]["money_maybe"] if pair and max(pair) < 0.6 else W["strip"]["money_read"]
        if reason == "not_in_record":  # say how sure the second check was that the record answers it
            pair = ((log or {}).get(f"{rec['id']}:router") or {}).get("answered")
            p = min(pair) if pair else None
            row["strip"] = W["strip"]["answer_close"] if p is not None and p >= 0.5 else W["strip"]["answer_none"]
    return row


def cmd_export(src, set_name):
    import subprocess
    recs = records(set_name)
    stand_in = src == "yardstick"
    source_obj = source(src, set_name)
    picked, results = core.decide(recs, source_obj)
    by_id = {r["id"]: r for r in recs}
    order = {"ready": 0, "person": 1, "do_not_contact": 2}
    log = getattr(source_obj, "log", {})
    rows = [page_row(by_id[r["id"]], r, log) for r in results]
    age = {r["id"]: (core.run_clock() - core.parse_time((r.get("message") or {}).get("at") or r["last_activity_at"])).total_seconds() for r in recs}
    rows.sort(key=lambda x: (order[x["outcome"]], 0 if x["ago"].startswith("Asked") else 1, age[x["id"]]))
    plan = json.loads(subprocess.run([sys.executable, str(HERE / "docs" / "sample_size.py"), "--json"], capture_output=True, text=True).stdout)
    line = None
    # the numbers as tested: one frozen scored run and six fresh sets, each read once, each key written first
    snaps = [HERE / "runs" / "scores-frozen-scored.json"] + [HERE / "runs" / f"scores-fresh{n}-at-test.json" for n in ("", "2", "3", "4", "5", "6")]
    tests = [json.loads(f.read_text())["readers"]["ai"] for f in snaps if f.exists()]
    sp = HERE / "scores.json"
    if tests and sp.exists() and not stand_in:
        wrong = sum(len(t["wrongly_ready"]) for t in tests)
        now = json.loads(sp.read_text())["readers"]["ai"]
        words = ["", "one", "two", "three", "four", "five", "six", "seven", "eight"]
        line = (f"In {words[len(tests)]} test sets, " + ("no one who needed a person was marked ready." if not wrong else f"{wrong} who needed a person were marked ready.") +
                f" On this page, {len(now['wrongly_held'])} of the {now['ready_keyed']} who didn't need one still went to a person.")
    counts = dict(core.counts(results), drafts=sum(1 for r in results if r.get("draft")))
    data = {"sample_date": "Nov 23, 2026", "counts": counts, "rows": rows, "stand_in": stand_in,
            "test_plan": plan, "scores": {"line": line} if line else None}
    out = HERE / "site" / "data" / "run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote site/data/run.json: {len(rows)} shoppers" + (" (fixed sentences standing in for the AI)" if stand_in else ""))


def main(argv):
    src = "saved"
    if "--source" in argv:
        i = argv.index("--source")
        src = argv[i + 1]
        del argv[i:i + 2]
    set_name = "scored"
    if "--set" in argv:
        i = argv.index("--set")
        set_name = argv[i + 1]
        del argv[i:i + 2]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    if argv[0] == "run":
        cmd_run(src, set_name)
        return 0
    if argv[0] == "export":
        cmd_export(src, set_name)
        return 0
    if argv[0] == "show" and len(argv) > 1:
        return cmd_show(argv[1], src, set_name)
    print(__doc__.strip())
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
