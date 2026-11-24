#!/usr/bin/env python3
"""The page shows exactly what the code decides: site/data/run.json matches a fresh run of the 40 from the saved drafts and checks."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import followup_core as core  # noqa: E402
import leftoff  # noqa: E402

page = json.loads((ROOT / "site" / "data" / "run.json").read_text())
recs = leftoff.records("scored")
_, results = core.decide(recs, leftoff.Saved("scored"))
by = {r["id"]: r for r in results}
bad = []
if {k: v for k, v in page["counts"].items() if k != "drafts"} != core.counts(results) or page["counts"].get("drafts") != sum(1 for r in results if r.get("draft")):
    bad.append(f"counts {page['counts']} vs {core.counts(results)}")
for row in page["rows"]:
    r = by.get(row["id"])
    if not r or row["outcome"] != r["outcome"]:
        bad.append(f"{row['id']}: page {row['outcome']}, code {r and r['outcome']}")
    elif r["outcome"] == "ready" and row["message"] != r.get("message"):
        bad.append(f"{row['id']}: message differs")
if len(page["rows"]) != len(results):
    bad.append(f"{len(page['rows'])} rows on the page, {len(results)} decided")
if page.get("stand_in"):
    bad.append("the page is showing the stand-in sentences")
print("ok   the page matches a fresh run of the 40" if not bad else "FAIL the page doesn't match the code:\n  " + "\n  ".join(bad))
sys.exit(1 if bad else 0)
