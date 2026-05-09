"""Collection helpers for Tawreed product catalog exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator

from .product_export_deduplicator import (
    count_duplicates_removed,
    deduplicate_products,
)


@dataclass(frozen=True)
class ProductExportCollection:
    """Unique collected product export candidates and scan counters."""

    candidates: list[dict[str, Any]]
    scanned_count: int
    duplicates_removed: int


@dataclass
class _ScanCounter:
    scanned_count: int = 0


def collect_unique_product_candidates(
    candidates: Iterable[dict[str, Any]], limit: int = 0
) -> ProductExportCollection:
    """Return unique candidates, applying limit to final unique products."""
    counter = _ScanCounter()
    counted_candidates = _count_candidates(candidates, counter)
    unique_candidates = list(_limit_candidates(
        deduplicate_products(counted_candidates), limit
    ))
    duplicates_removed = count_duplicates_removed(
        counter.scanned_count, len(unique_candidates)
    )
    return ProductExportCollection(
        candidates=unique_candidates,
        scanned_count=counter.scanned_count,
        duplicates_removed=duplicates_removed,
    )


def product_export_collection_summary(collection: ProductExportCollection) -> str:
    """Return a concise export collection log message."""
    return (
        "Tawreed products scanned: "
        f"{collection.scanned_count}; unique exported: {len(collection.candidates)}; "
        f"duplicates removed: {collection.duplicates_removed}"
    )


def _count_candidates(
    candidates: Iterable[dict[str, Any]], counter: _ScanCounter
) -> Iterator[dict[str, Any]]:
    for candidate in candidates:
        counter.scanned_count += 1
        yield candidate


def _limit_candidates(
    candidates: Iterable[dict[str, Any]], limit: int
) -> Iterator[dict[str, Any]]:
    iterator = iter(candidates)
    emitted = 0
    while not limit or emitted < limit:
        try:
            candidate = next(iterator)
        except StopIteration:
            return
        yield candidate
        emitted += 1
