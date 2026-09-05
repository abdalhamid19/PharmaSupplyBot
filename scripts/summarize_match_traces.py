"""Summarize match-trace JSONL artifacts.

Reads every JSONL file under ``artifacts/match_traces/`` (or the file
passed via ``--path``) and prints a per-tier breakdown: how many
``match_brand`` calls landed in each tier, the per-tier average
score, and the top winning reasons.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _winning_tier(record: dict) -> str:
    """Classify a trace record by the tier that produced the final score."""
    if record["final_score"] <= 0.0:
        return "no_match"
    if record["tier1_tawreed"]["score"] > 0:
        return "1_tawreed"
    if record["tier2_karem505"]["score"] > 0:
        return "2_karem505"
    if record["tier3_cache"]["score"] >= 0.6:
        return "3_translation"
    return "unknown"


def _summarize(path: Path) -> dict:
    by_tier: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    by_score_sum: defaultdict[str, float] = defaultdict(float)
    by_score_count: defaultdict[str, int] = defaultdict(int)
    by_tier_attempt: Counter[str] = Counter()
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        n += 1
        # Per-tier attempt counts (which tiers fired for each call)
        if rec["tier1_tawreed"]["score"] > 0:
            by_tier_attempt["1_tawreed"] += 1
        if rec["tier2_karem505"]["score"] > 0:
            by_tier_attempt["2_karem505"] += 1
        if rec["tier3_cache"]["score"] > 0:
            by_tier_attempt["3_cache"] += 1
        # Winning tier
        tier = _winning_tier(rec)
        by_tier[tier] += 1
        by_score_sum[tier] += rec["final_score"]
        by_score_count[tier] += 1
        by_reason[rec["winning_reason"]] += 1
    return {
        "file": str(path),
        "total_calls": n,
        "by_tier_attempt": dict(by_tier_attempt),
        "by_tier": dict(by_tier),
        "by_tier_avg_score": {
            t: round(by_score_sum[t] / max(by_score_count[t], 1), 3)
            for t in by_score_sum
        },
        "top_reasons": by_reason.most_common(5),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", help="Single JSONL file (default: all under artifacts/match_traces)")
    args = parser.parse_args()

    if args.path:
        files = [Path(args.path)]
    else:
        files = sorted(Path("artifacts/match_traces").glob("*.jsonl"))
    if not files:
        print("no match-trace files found")
        return

    for f in files:
        s = _summarize(f)
        print(f"=== {s['file']} ===")
        print(f"  total calls: {s['total_calls']}")
        print(f"  tier attempts (which tier produced a non-zero signal):")
        for tier in ["1_tawreed", "2_karem505", "3_cache"]:
            count = s["by_tier_attempt"].get(tier, 0)
            if count:
                pct = 100.0 * count / s["total_calls"]
                print(f"    {tier:18s}: {count:4d}  ({pct:.1f}%)")
        print(f"  winning tier (drives final score):")
        for tier in ["1_tawreed", "2_karem505", "3_translation", "no_match", "unknown"]:
            count = s["by_tier"].get(tier, 0)
            avg = s["by_tier_avg_score"].get(tier, 0)
            if count:
                pct = 100.0 * count / s["total_calls"]
                print(f"    {tier:18s}: {count:4d}  ({pct:.1f}%)  (avg {avg:.2f})")
        print("  top winning reasons:")
        for reason, count in s["top_reasons"]:
            print(f"    {count:4d}  {reason[:80]}")
        print()


if __name__ == "__main__":
    main()
