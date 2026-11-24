#!/usr/bin/env python3
"""How many quiet shoppers the test needs.

Two groups: shoppers who get the nudge and shoppers held back. The question is whether the share who move one step
on within 14 days is higher with the nudge. The base rate below is a guess, said as one everywhere it appears,
until real numbers replace it.

    python3 docs/sample_size.py            # the plan's numbers and a small table
    python3 docs/sample_size.py --json     # the same, for the page and the tests
"""
import json
import math
import sys
from statistics import NormalDist

BASE = 0.08        # a guess: 8 in 100 move one step on within 14 days without the nudge
GAIN = 0.015       # the smallest gain worth finding: 1.5 per 100
ALPHA = 0.05       # two-sided chance of calling a win that isn't there
POWER = 0.80       # chance of seeing a real gain of that size
HELD_SHARE = 0.20  # 1 in 5 held back


def held_back_needed(base, gain, held_share, alpha=ALPHA, power=POWER, pooled=True):
    """Shoppers needed in the held-back group (normal approximation for two proportions, unequal groups)."""
    r = (1 - held_share) / held_share          # nudged per held back
    p0, p1 = base, base + gain
    za, zb = NormalDist().inv_cdf(1 - alpha / 2), NormalDist().inv_cdf(power)
    spread = math.sqrt(p0 * (1 - p0) + p1 * (1 - p1) / r)
    if pooled:
        pbar = (p0 + r * p1) / (1 + r)
        first = za * math.sqrt(pbar * (1 - pbar) * (1 + 1 / r))
    else:
        first = za * spread
    return math.ceil(((first + zb * spread) / gain) ** 2), r


def plan(base=BASE, gain=GAIN, held_share=HELD_SHARE, pooled=True):
    held, r = held_back_needed(base, gain, held_share, pooled=pooled)
    nudged = math.ceil(held * r)
    return {"held_back": held, "nudged": nudged, "total": held + nudged}


def main(argv):
    out = {
        "assumptions": {"base_per_100": BASE * 100, "gain_per_100": GAIN * 100, "two_sided_alpha": ALPHA, "power": POWER,
                        "held_back_share": HELD_SHARE, "base_is_a_guess": True},
        "cautious": plan(pooled=True),
        "other_formula": plan(pooled=False),
        "one_in_two": plan(held_share=0.5),
        "one_in_ten": plan(held_share=0.10),
        "table": [{"base_per_100": round(b * 100), "gain_per_100": g * 100, **plan(base=b, gain=g)}
                  for b in (0.05, 0.08, 0.12) for g in (0.01, 0.015, 0.02)],
    }
    if "--json" in argv:
        print(json.dumps(out, indent=1))
        return
    c, o = out["cautious"], out["other_formula"]
    print(f"Base {BASE * 100:.0f} in 100 (a guess), gain {GAIN * 100} per 100, {POWER:.0%} power, two-sided {ALPHA}, 1 in 5 held back:")
    print(f"  {c['total']:,} shoppers ({c['held_back']:,} held back, {c['nudged']:,} nudged); the other common formula gives {o['total']:,}")
    print(f"  1 in 2 held back: {out['one_in_two']['total']:,} ({out['one_in_two']['held_back']:,} held back)")
    print(f"  1 in 10 held back: {out['one_in_ten']['total']:,} ({out['one_in_ten']['held_back']:,} held back)")
    print("  base  gain  total")
    for t in out["table"]:
        print(f"  {t['base_per_100']:>4}  {t['gain_per_100']:>4}  {t['total']:>7,}")


if __name__ == "__main__":
    main(sys.argv[1:])
