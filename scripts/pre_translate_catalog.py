"""Pre-translate the unique Arabic names in one Excel target catalog.

Reads a single Excel file, pulls the product-name column, dedupes the
values, and translates everything that isn't already in the
persistent cache using Cohere's batch endpoint (50 names per call).

Usage::

    python scripts/pre_translate_catalog.py ^
        --excel "data/input/excel target/البركة شركات.xlsx" ^
        --name-col الصنف ^
        --batch-size 50

The script is idempotent: re-running it is cheap because the cache
short-circuits already-translated names. It also supports
``--dry-run`` to print the call count + estimated time without
hitting the network.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=False)
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402

from src.core.database.translation_cache import (  # noqa: E402
    TranslationCache,
    normalize_key,
)
from src.core.normalization.translation import (  # noqa: E402
    MAX_BATCH_SIZE,
    RATE_LIMIT_PER_MIN,
    ar_to_en_many,
)


def _load_names(excel_path: Path, name_col: str) -> list[str]:
    df = pd.read_excel(excel_path, dtype=str).fillna("")
    if name_col not in df.columns:
        raise SystemExit(
            f"Column {name_col!r} not found. Available: {list(df.columns)}"
        )
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in df[name_col].tolist():
        name = str(raw or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel", required=True, help="Path to the Excel target file")
    parser.add_argument(
        "--name-col",
        default="الصنف",
        help="Column name in the Excel that holds the Arabic product name",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("COHERE_BATCH_SIZE", "50")),
        help="How many names to send per Cohere call (maximum: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the call count and cost estimate without translating",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel)
    if not excel_path.exists():
        raise SystemExit(f"Excel file not found: {excel_path}")

    names = _load_names(excel_path, args.name_col)
    print(f"unique arabic names: {len(names)}")

    cache = TranslationCache()
    cached = cache.get_many(names)
    pending = [n for n in names if normalize_key(n) not in cached]
    print(f"already cached: {len(cached)}")
    print(f"to translate: {len(pending)}")

    if not pending:
        print("nothing to do; cache hit 100%")
        return

    batch_size = min(max(1, args.batch_size), MAX_BATCH_SIZE)
    n_calls = (len(pending) + batch_size - 1) // batch_size
    est_seconds = n_calls * 60.0 / max(1, RATE_LIMIT_PER_MIN)
    print(
        f"plan: {n_calls} calls (batch_size={batch_size}); "
        f"~{est_seconds:.0f}s at {RATE_LIMIT_PER_MIN}/min"
    )

    if args.dry_run:
        return

    started = time.monotonic()
    translated = ar_to_en_many(pending, batch_size=batch_size)
    elapsed = time.monotonic() - started
    print(
        f"translated: {len(translated)} in {elapsed:.1f}s "
        f"({len(translated) / max(elapsed, 1):.1f} names/s)"
    )

    stats = cache.stats()
    print(
        f"cache now holds {stats['entries']} entries "
        f"({stats['total_hits']} hits since boot)"
    )


if __name__ == "__main__":
    main()
