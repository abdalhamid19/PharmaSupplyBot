"""Walk through ONE item's match-trace and print every candidate row tested."""
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "artifacts/match_traces/one_item.jsonl"
    )
    target_query = sys.argv[2] if len(sys.argv) > 2 else None
    by_item: dict[str, list[dict]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        by_item[rec["en_query"]].append(rec)

    if target_query is None:
        target_query = next(iter(by_item))
    recs = by_item[target_query]
    recs.sort(key=lambda r: -r["final_score"])

    print(f"=== {target_query} ===")
    print(f"candidates tested: {len(recs)}")
    print()
    for i, r in enumerate(recs, 1):
        winner = "★" if r["final_score"] > 0 else " "
        t1 = r["tier1_tawreed"]
        t2 = r["tier2_karem505"]
        t3 = r["tier3_cache"]
        print(f"{winner} #{i:3d}  ar_row={r['ar_row']!r}")
        if t1['score'] > 0:
            print(f"         T1 (Tawreed)   = {t1['score']:.2f}  reason={t1['reason']!r}")
        if t2['score'] > 0:
            print(f"         T2 (karem505)  = {t2['score']:.2f}  reason={t2['reason']!r}")
        if t3['score'] > 0:
            print(f"         T3 (Cohere)    = {t3['score']:.2f}  trans={t3['translation']!r}")
        print(f"         compat={r['compatibility_factor']:.2f}  final={r['final_score']:.2f}  ({r['winning_reason']})")
        print()


if __name__ == "__main__":
    main()
