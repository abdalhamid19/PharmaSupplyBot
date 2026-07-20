"""Quick inspection of the local manual-review SQLite database."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.manual_review.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewStore,
)


def main() -> None:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MANUAL_REVIEW_DB
    print(f"Database: {db_path}")
    if not db_path.exists():
        print("File does not exist yet.")
        return

    store = ManualReviewStore(db_path)
    decisions = store.list_decisions()
    print(f"Total records: {len(decisions)}")
    print("\nSample records:")
    for decision in decisions[:5]:
        print(
            decision.item_code,
            decision.item_name,
            decision.approved,
            decision.manual_decision,
            decision.correct_product_name,
        )


if __name__ == "__main__":
    main()
