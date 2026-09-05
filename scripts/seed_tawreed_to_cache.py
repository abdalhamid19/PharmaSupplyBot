"""Seed the persistent translation cache from the Tawreed product catalog.

The Tawreed catalog (49K products, Arabic+English trade names) is the
cheapest, highest-quality translation source we have: every row is a
real product the bot already knows. Pre-loading the cache with it
means subsequent runs of the bilingual matcher need zero Cohere
calls for any product that exists in Tawreed.

The script also accepts a target Excel file (e.g. البركة شركات.xlsx)
to pre-translate just the names in that catalog. Without ``--excel``
it processes every unique Arabic name in Tawreed.

Usage::

    python scripts/seed_tawreed_to_cache.py
    python scripts/seed_tawreed_to_cache.py --dry-run
    python scripts/seed_tawreed_to_cache.py ^
        --excel "data/input/excel target/البركة شركات.xlsx" ^
        --name-col الصنف
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402
from rapidfuzz import fuzz, process  # noqa: E402

from src.core.database.translation_cache import TranslationCache  # noqa: E402
from src.core.normalization.tawreed_catalog import (  # noqa: E402
    collapse_ws,
    load_tawreed_catalog,
)


def _load_target_names(excel_path: Path, name_col: str) -> list[str]:
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


def _fuzzy_match(
    ar_name: str, tawreed_collapsed: list[str], score_cutoff: int = 85
) -> str | None:
    """Find the best Tawreed collapsed-Arabic name above the threshold.

    Returns the English name for the best match, or None.
    """
    best = process.extractOne(
        ar_name,
        tawreed_collapsed,
        scorer=fuzz.token_set_ratio,
        score_cutoff=score_cutoff,
    )
    if not best:
        return None
    return best[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--excel",
        help="Optional target Excel file. When given, only translates names in it.",
    )
    parser.add_argument("--name-col", default="الصنف")
    parser.add_argument(
        "--fuzzy-cutoff",
        type=int,
        default=80,
        help="Minimum token_set_ratio to accept a fuzzy match (default 80)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report counts without writing"
    )
    args = parser.parse_args()

    catalog = load_tawreed_catalog()
    tawreed_collapsed = list(catalog["by_ar"].keys())
    tawreed_by_key = catalog["by_ar"]
    print(f"tawreed catalog: {len(catalog['rows'])} rows, "
          f"{len(tawreed_collapsed)} unique collapsed ar names")

    if args.excel:
        target_names = _load_target_names(Path(args.excel), args.name_col)
        print(f"target names (from {args.excel}): {len(target_names)}")
    else:
        target_names = []
        for ar in catalog["by_ar"]:
            target_names.append(ar)
        print(f"target names (from tawreed): {len(target_names)}")

    cache = TranslationCache()
    cached = cache.get_many_by_raw(target_names)
    pending = [n for n in target_names if n not in cached]
    print(f"already cached: {len(cached)}, to attempt: {len(pending)}")

    direct = 0
    fuzzy = 0
    missed = 0
    new_entries: dict[str, str] = {}
    started = time.monotonic()

    for ar_name in pending:
        cn = collapse_ws(ar_name)
        if cn in tawreed_by_key:
            rows = tawreed_by_key[cn]
            new_entries[ar_name] = rows[0]["en"]
            direct += 1
            continue
        hit = _fuzzy_match(cn, tawreed_collapsed, args.fuzzy_cutoff)
        if hit is not None:
            rows = tawreed_by_key[hit]
            new_entries[ar_name] = rows[0]["en"]
            fuzzy += 1
            continue
        missed += 1

    elapsed = time.monotonic() - started
    print(
        f"resolved in {elapsed:.1f}s — direct: {direct}, "
        f"fuzzy: {fuzzy}, missed: {missed}"
    )

    if args.dry_run:
        print("(dry run: nothing written)")
        return

    if new_entries:
        cache.put_many(new_entries, model="tawreed_catalog_seed")
    print(f"cache updated: +{len(new_entries)} entries")
    print(f"final cache: {cache.stats()}")


if __name__ == "__main__":
    main()
