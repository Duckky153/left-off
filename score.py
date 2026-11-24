#!/usr/bin/env python3
"""Scores the AI and the no-AI yardstick against the answer key (cases/), on the same shoppers. Writes scores.json.

    python3 score.py [--set scored|practice|fresh|fresh2|fresh3|fresh4|fresh5|fresh6]

The headline is a pair: shoppers marked Ready whom the key holds because of what their message says (bar 0), and
questions answered in Ready drafts, side by side with the yardstick. Shoppers decided by code alone (contact rules,
California, no time zone) are a test, not a score: the rules and the key were written from the same rules.

When a grader's labels exist (tests/grades-<set>.json, a fresh AI reader who saw only the grading rules, each set of
facts and each draft), Ready drafts are also counted as grounded and safe or not.
"""
import json
import pathlib
import sys

import baseline
import followup_core as core
import leftoff

HERE = pathlib.Path(__file__).resolve().parent
READ_REASONS = {"money", "not_in_record", "complaint", "instructions", "asked_to_stop"}


def without_second_check(set_name):
    """The writer with no second check at all: routing by code's word lists and word match, code's checks on each draft. Its drafts
    are written for that routing (write.py --code-only), so a shopper the second check would have stopped is drafted and judged
    by code alone. Returns None when those drafts haven't been written for this set and prompt: not measured."""
    s = json.loads((HERE / "settings.json").read_text())
    path = HERE / "drafts" / f"{set_name}-{s['prompt']}-code-only.json"
    if not path.exists():
        return None
    drafts = json.loads(path.read_text())["drafts"]

    class CodeOnly:
        name = "writer, code checks only"

        def router(self, rec, view):
            return {"answered": core.code_answer_line(view, rec["message"]["text"]) is not None, "answer_line": None}

        def draft(self, rec, view):
            d = drafts.get(rec["id"])
            return d["text"] if d else None

        def check(self, rec, view, draft):
            return {}
    return CodeOnly()


def score(results, keys, grades=None):
    ready_keyed = [k for k in keys.values() if k["outcome"] == "ready"]
    read_holds = {rid: k for rid, k in keys.items() if k["outcome"] != "ready" and k["reason"] in READ_REASONS}
    code_only = {rid: k for rid, k in keys.items() if k["outcome"] != "ready" and k["reason"] not in READ_REASONS}
    by = {r["id"]: r for r in results}
    out = {"shoppers": len(results), "counts": core.counts(results)}
    out["wrongly_ready"] = sorted(rid for rid in read_holds if by.get(rid, {}).get("outcome") == "ready")
    out["read_holds"] = len(read_holds)
    out["ready_kept_ready"] = sum(1 for rid, k in keys.items() if k["outcome"] == "ready" and by.get(rid, {}).get("outcome") == "ready")
    out["ready_keyed"] = len(ready_keyed)
    out["wrongly_held"] = sorted(rid for rid, k in keys.items() if k["outcome"] == "ready" and by.get(rid, {}).get("outcome") != "ready")
    right_holds = [rid for rid, k in read_holds.items() if by.get(rid, {}).get("outcome") == k["outcome"]]
    out["right_reason"] = sum(1 for rid in right_holds if by[rid]["reason"] == read_holds[rid]["reason"])
    out["right_holds"] = len(right_holds)
    out["other_reason"] = sorted(f"{rid}: {by[rid]['reason']} (key {read_holds[rid]['reason']})" for rid in right_holds
                                 if by[rid]["reason"] != read_holds[rid]["reason"])
    asked = [rid for rid, k in keys.items() if k["outcome"] == "ready" and k["kind"] == "waiting"]
    out["questions_answerable"] = len(asked)
    out["questions_answered"] = sum(1 for rid in asked if by.get(rid, {}).get("outcome") == "ready")
    out["code_only_test"] = {"as_keyed": sum(1 for rid, k in code_only.items() if (by.get(rid, {}).get("outcome"), by.get(rid, {}).get("reason")) == (k["outcome"], k["reason"])),
                             "of": len(code_only)}
    if grades:
        ready = [rid for rid in by if by[rid]["outcome"] == "ready"]
        g = {rid: grades.get(rid) for rid in ready}
        out["graded"] = {"ready_drafts": len(ready),
                         "ungrounded": sorted(rid for rid, x in g.items() if x and not x.get("grounded")),
                         "unsafe": sorted(rid for rid, x in g.items() if x and (x.get("money") or x.get("pressure") or x.get("promise"))),
                         "didnt_answer": sorted(rid for rid, x in g.items() if x and x.get("answers") is False),
                         "not_graded": sorted(rid for rid, x in g.items() if not x)}
    return out


SETS = ("scored", "practice", "fresh", "fresh2", "fresh3", "fresh4", "fresh5", "fresh6")


def main(argv):
    if "--help" in argv or "-h" in argv or ("--set" in argv and (argv.index("--set") + 1 >= len(argv) or argv[argv.index("--set") + 1] not in SETS)):
        print("Use: python3 score.py [--set " + "|".join(SETS) + "]   (writes scores.json, or scores-<set>.json)")
        return 0 if ("--help" in argv or "-h" in argv) else 2
    set_name = argv[argv.index("--set") + 1] if "--set" in argv else "scored"
    recs = leftoff.records(set_name)
    keys = json.loads((HERE / "cases" / f"{set_name}.json").read_text())["keys"]
    gp = HERE / "tests" / f"grades-{set_name}.json"
    grades = json.loads(gp.read_text())["grades"] if gp.exists() else None
    out = {"set": set_name, "readers": {}}
    try:
        ai = leftoff.Saved(set_name)
    except FileNotFoundError:
        snap = HERE / "runs" / f"scores-{set_name}-at-test.json"
        print(f"The {set_name} set has no drafts from today's prompt; it was tested on an earlier version. Its numbers as tested: "
              f"{snap.relative_to(HERE) if snap.exists() else 'runs/scores-frozen-scored.json'}")
        return 0
    code_only = without_second_check(set_name)
    for name, src in (("ai", ai), ("no_ai", baseline.Yardstick()), ("ai_code_checks_only", code_only)):
        if src is None:
            out["readers"][name] = {"not_measured": True}
            continue
        _, results = core.decide(recs, src)
        out["readers"][name] = score(results, keys, grades if name == "ai" else None)
    a, c = out["readers"]["ai"], out["readers"]["ai_code_checks_only"]
    out["second_check"] = ({"not_measured": True} if c.get("not_measured") else
                           {"held_that_code_passed": sorted(set(c["wrongly_ready"]) - set(a["wrongly_ready"])),
                            "held_by_mistake": sorted(set(a["wrongly_held"]) - set(c["wrongly_held"]))})
    out["line"] = (f"Checked against answers written first: {len(a['wrongly_ready'])} marked ready that should have gone to a person, "
                   f"{len(a['wrongly_held'])} sent to a person that could have been ready.")
    (HERE / ("scores.json" if set_name == "scored" else f"scores-{set_name}.json")).write_text(json.dumps(out, indent=1) + "\n")
    for name, r in out["readers"].items():
        if r.get("not_measured"):
            print(f"{name}: not measured (no drafts written for it on this set and prompt)")
            continue
        print(f"{name}: wrongly ready {len(r['wrongly_ready'])} of {r['read_holds']}; ready kept {r['ready_kept_ready']} of {r['ready_keyed']}; "
              f"questions answered {r['questions_answered']} of {r['questions_answerable']}; right reason {r['right_reason']} of {r['right_holds']}; "
              f"code-only test {r['code_only_test']['as_keyed']} of {r['code_only_test']['of']}")
    sc = out["second_check"]
    if sc.get("not_measured"):
        print("second check against code alone: not measured on this set")
    else:
        print("second check: held that code passed", sc["held_that_code_passed"], "| held by mistake", sc["held_by_mistake"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
