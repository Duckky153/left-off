#!/usr/bin/env python3
"""Planning comparison on the practice set only: two writer models drafting from the same facts, with the practice
answer key standing in for the first read so every answerable question gets a draft. Nothing here is scored.

    python3 tests/compare_writers.py <model> <prompt-file> <tag>
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import write  # noqa: E402
from key_check import KeyStandIn  # noqa: E402
import leftoff  # noqa: E402

model, prompt_file, tag = sys.argv[1], sys.argv[2], sys.argv[3]
ks = KeyStandIn(json.loads((ROOT / "cases" / "practice.json").read_text())["keys"])
router = {r["id"]: {"router": ks.router(r, None)} for r in leftoff.records("practice") if r["id"] in ks.keys}
write.run("practice", "candidate", model=model, tag=tag, prompt_file=prompt_file, router_override=router)
