"""Walk a match-trace JSONL and print per-item breakdown.

For every (en_query) group we show:
  * how many candidate rows were tested
  * the winning tier (if any)
  * the highest scoring tier-3 cache attempt (translation)
  * the highest scoring tier-1 (tawreed) attempt, if any
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _tier_fired(rec: dict) -> dict:
    return {
        "t1": rec["tier1_tawreed"]["score"],
        "t2": rec["tier2_karem505"]["score"],
        "t3": rec["tier3_cache"]["score"],
    }


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "artifacts/match_traces/wardany_50.jsonl"
    )
    by_item: dict[str, list[dict]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        by_item[rec["en_query"]].append(rec)

    print(f"=== {path} ===")
    print(f"items: {len(by_item)}")
    for query, recs in list(by_item.items())[:25]:
        winners = [r for r in recs if r["final_score"] > 0]
        t1 = [r for r in recs if r["tier1_tawreed"]["score"] > 0]
        t2 = [r for r in recs if r["tier2_karem505"]["score"] > 0]
        t3_attempted = [r for r in recs if r["tier3_cache"]["score"] > 0]
        best = max(recs, key=lambda r: r["final_score"]) if recs else None
        best_t3 = max(t3_attempted, key=lambda r: r["tier3_cache"]["score"]) if t3_attempted else None
        best_t1 = max(t1, key=lambda r: r["tier1_tawreed"]["score"]) if t1 else None
        best_t2 = max(t2, key=lambda r: r["tier2_karem505"]["score"]) if t2 else None
        print(f"\n{query}")
        print(f"  candidates tested : {len(recs)}")
        print(f"  tier 1 (Tawreed)  : {len(t1)} attempts" + (f", best score={best_t1['tier1_tawreed']['score']:.2f}" if best_t1 else ""))
        print(f"  tier 2 (karem505) : {len(t2)} attempts" + (f", best score={best_t2['tier2_karem505']['score']:.2f}" if best_t2 else ""))
        print(f"  tier 3 (cache)    : {len(t3_attempted)} attempts" + (f", best score={best_t3['tier3_cache']['score']:.2f}" if best_t3 else ""))
        if best and best["final_score"] > 0:
            print(f"  WINNER            : score={best['final_score']:.2f}  ({best['winning_reason']})")
            print(f"                       ar_row : {best['ar_row']}")
        else:
            print(f"  NO WINNER         : best={best['final_score'] if best else 0:.2f}")


if __name__ == "__main__":
    main()
