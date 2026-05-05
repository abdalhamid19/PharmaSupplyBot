"""Chunking helpers for distributing work across parallel item workers."""

from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")


def split_into_chunks(items: Sequence[T], worker_count: int) -> list[list[T]]:
    """Split items into contiguous chunks, one per worker, dropping empty ones."""
    materialized = list(items)
    effective_workers = max(1, int(worker_count))
    if not materialized:
        return []
    if effective_workers == 1 or effective_workers >= len(materialized):
        return _one_chunk_per_item_when_oversized(materialized, effective_workers)
    return _balanced_chunks(materialized, effective_workers)


def _one_chunk_per_item_when_oversized(
    materialized: list[T], effective_workers: int
) -> list[list[T]]:
    """Return single chunk or one-item-per-worker when workers meet or exceed items."""
    if effective_workers == 1:
        return [materialized]
    return [[item] for item in materialized]


def _balanced_chunks(materialized: list[T], effective_workers: int) -> list[list[T]]:
    """Return contiguous balanced chunks when there are fewer workers than items."""
    total = len(materialized)
    base_size, remainder = divmod(total, effective_workers)
    chunks: list[list[T]] = []
    start = 0
    for worker_index in range(effective_workers):
        take = base_size + (1 if worker_index < remainder else 0)
        chunks.append(materialized[start:start + take])
        start += take
    return [chunk for chunk in chunks if chunk]
