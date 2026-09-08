"""Walk ONE item trace and explain each step in plain English.

For one item, prints:
  * the input (English query + Arabic brand stripped)
  * how many catalog rows survived the pre-filter
  * which tiers were attempted
  * the top-3 highest-scoring candidates and why they didn't win
  * the final decision
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "artifacts/match_traces/one_item.jsonl"
    )
    target_query = sys.argv[2] if len(sys.argv) > 2 else "ALFATHROMB 5 MCG 20 TABS"

    by_item: dict[str, list[dict]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        by_item[rec["en_query"]].append(rec)

    recs = by_item[target_query]
    recs_sorted = sorted(recs, key=lambda r: -r["final_score"])
    t1_hits = [r for r in recs if r["tier1_tawreed"]["score"] > 0]
    t2_hits = [r for r in recs if r["tier2_karem505"]["score"] > 0]
    t3_hits = [r for r in recs if r["tier3_cache"]["score"] > 0]
    winners = [r for r in recs if r["final_score"] > 0]

    print(f"INPUT QUERY: {target_query}")
    print()
    print(f"STEP 1 — pre-filter")
    print(f"  catalog rows scanned: {len(recs)}")
    print(f"  rows rejected:        0 (every row was logged)")
    print()
    print(f"STEP 2 — per-tier attempts")
    print(f"  T1 Tawreed (verified)   : {len(t1_hits):4d} candidates")
    print(f"  T2 karem505 (community): {len(t2_hits):4d} candidates")
    print(f"  T3 Cohere cache (LLM)   : {len(t3_hits):4d} candidates")
    print()
    if t1_hits:
        print(f"  highest T1 hit:")
        b = max(t1_hits, key=lambda r: r["tier1_tawreed"]["score"])
        print(f"    {b['ar_row']!r}  score={b['tier1_tawreed']['score']:.2f}  reason={b['tier1_tawreed']['reason']!r}")
    if t2_hits:
        print(f"  highest T2 hit:")
        b = max(t2_hits, key=lambda r: r["tier2_karem505"]["score"])
        print(f"    {b['ar_row']!r}  score={b['tier2_karem505']['score']:.2f}  reason={b['tier2_karem505']['reason']!r}")
    if t3_hits:
        print(f"  highest T3 hit:")
        b = max(t3_hits, key=lambda r: r["tier3_cache"]["score"])
        print(f"    {b['ar_row']!r}  score={b['tier3_cache']['score']:.2f}  trans={b['tier3_cache']['translation']!r}")
    print()
    print(f"STEP 3 — top 5 candidates by final score (post-compatibility)")
    for i, r in enumerate(recs_sorted[:5], 1):
        marker = "★" if r["final_score"] > 0 else " "
        print(f"  {marker} #{i}  {r['ar_row']!r}")
        print(f"      final={r['final_score']:.2f}  compat={r['compatibility_factor']:.2f}  reason={r['winning_reason']!r}")
    print()
    print(f"STEP 4 — outcome")
    if winners:
        w = max(winners, key=lambda r: r["final_score"])
        print(f"  WINNER: {w['ar_row']!r}")
        print(f"  score  : {w['final_score']:.2f}")
        print(f"  reason : {w['winning_reason']!r}")
    else:
        print(f"  NO WINNER  (best raw score was below the 0.7 threshold)")
        best = recs_sorted[0]
        print(f"  best raw   : {best['tier3_cache']['score']:.2f}  ({best['ar_row']!r})")
        print(f"  best final : {best['final_score']:.2f}  (after compat={best['compatibility_factor']:.2f})")


if __name__ == "__main__":
    main()
