#!/usr/bin/env python3
"""The answer key standing in for every AI part: the second check's answers come from the key, and the drafts are the
yardstick's fixed sentences. With that, every shopper must come out as keyed and the four outside the queue must stay
out. This tests the rules and the wiring, not any AI. (A test, not a score.)

    python3 tests/key_check.py [scored|practice]

The key also stands in for code's own answer-line match, so a wording that code fails to match shows up in the scored
run, not here.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import baseline  # noqa: E402
import followup_core as core  # noqa: E402

ROUTER_REASONS = {"money", "complaint", "instructions"}


class KeyStandIn:
    name = "the answer key"

    def __init__(self, keys):
        self.keys = keys

    def router(self, rec, view):
        k = self.keys[rec["id"]]
        if k["outcome"] == "do_not_contact" and k["reason"] == "asked_to_stop":
            return {"asks_to_stop": True}
        if k["outcome"] == "person" and k["reason"] in ROUTER_REASONS:
            return {"reason": k["reason"]}
        if k["outcome"] == "person" and k["reason"] == "not_in_record":
            return {"answered": False}
        return {"answered": True, "answer_line": k.get("answer_line")}

    def draft(self, rec, view):
        return baseline.draft_for(view)

    def check(self, rec, view, draft):
        return {}


def main(set_name):
    f = {"scored": "shoppers.json", "practice": "practice.json", "fresh": "fresh.json", "fresh2": "fresh2.json", "fresh3": "fresh3.json", "fresh4": "fresh4.json", "fresh5": "fresh5.json", "fresh6": "fresh6.json"}[set_name]
    recs = json.loads((ROOT / "sample" / f).read_text())["shoppers"]
    keys = json.loads((ROOT / "cases" / f"{set_name}.json").read_text())["keys"]
    # the key stands in for the whole read of a message, code's own answer match included, so this tests the wiring
    by_text = {r["message"]["text"]: keys[r["id"]] for r in recs if r["id"] in keys and r.get("message")}
    real_line, real_feat = core.code_answer_line, core.feature_asked

    def line_for(view, q):
        return by_text[q]["answer_line"] if q in by_text else real_line(view, q)

    def feat_for(view, q):
        if q in by_text:
            hit = real_feat(view, q)
            return hit if hit else (dict(view["lines"]).get("LISTED FEATURES", "").split("; ")[0], True)
        return real_feat(view, q)

    core.code_answer_line, core.feature_asked = line_for, feat_for
    picked, results = core.decide(recs, KeyStandIn(keys))
    core.code_answer_line, core.feature_asked = real_line, real_feat
    bad = []
    outside = [r["id"] for r in recs if r["id"] not in keys]
    for rid in outside:
        if rid in picked:
            bad.append(f"{rid}: outside the queue, but the query picked it")
    for rid in keys:
        if rid not in picked:
            bad.append(f"{rid}: keyed, but the query didn't pick it")
    for r in results:
        k = keys.get(r["id"])
        if not k:
            continue
        if (r["outcome"], r["reason"]) != (k["outcome"], k["reason"]):
            extra = "; " + "; ".join(f"{a} {b}" for a, b in r.get("failed", [])) if r.get("failed") else ""
            bad.append(f"{r['id']} (slot {k['slot']}): got {r['outcome']} {r['reason']}, keyed {k['outcome']} {k['reason']}{extra}")
        elif k.get("channel") and r.get("channel") != k["channel"]:
            bad.append(f"{r['id']} (slot {k['slot']}): channel {r.get('channel')}, keyed {k['channel']}")
    c = core.counts(results)
    print(f"{set_name}: {len(picked)} in the queue of {len(recs)}; {c['ready']} ready, {c['person']} for a person, {c['do_not_contact']} do not contact")
    for b in bad:
        print("  NOT AS KEYED " + b)
    print("all as keyed" if not bad else f"{len(bad)} not as keyed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main((sys.argv[1:] or ["scored"])[0]))
