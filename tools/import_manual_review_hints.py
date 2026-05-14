"""Export approved manual-review corrections into reusable matching hints."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.manual_review_hints import export_manual_review_hints


def main() -> int:
    """Run the manual-review hint export command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manual_review_csv")
    parser.add_argument(
        "--output",
        default="data/manual_review_hints.json",
        help="Output JSON path for approved correction hints",
    )
    args = parser.parse_args()
    count = export_manual_review_hints(args.manual_review_csv, args.output)
    print(f"manual_review_hints_exported:{count}")
    print(f"output:{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
