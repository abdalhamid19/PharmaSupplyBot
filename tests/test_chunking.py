"""Tests for the item chunking helper."""

from __future__ import annotations

import unittest

from src.core.utils.chunking import split_into_chunks


class SplitIntoChunksTests(unittest.TestCase):
    """Contract tests for split_into_chunks across edge and typical inputs."""

    def test_returns_empty_when_input_is_empty(self) -> None:
        """Empty sequences produce no chunks regardless of worker count."""
        self.assertEqual(split_into_chunks([], 3), [])

    def test_single_worker_returns_one_chunk(self) -> None:
        """Worker count of one collapses everything into a single chunk."""
        self.assertEqual(split_into_chunks([1, 2, 3], 1), [[1, 2, 3]])

    def test_zero_or_negative_workers_collapses_to_single_chunk(self) -> None:
        """Non-positive worker counts behave like a single worker."""
        self.assertEqual(split_into_chunks([1, 2, 3], 0), [[1, 2, 3]])
        self.assertEqual(split_into_chunks([1, 2, 3], -5), [[1, 2, 3]])

    def test_workers_exceed_items_yields_one_item_per_chunk(self) -> None:
        """When workers outnumber items each chunk holds exactly one item."""
        self.assertEqual(split_into_chunks([1, 2], 5), [[1], [2]])

    def test_even_split(self) -> None:
        """Equal distribution splits the list into equal-sized contiguous slices."""
        self.assertEqual(split_into_chunks([1, 2, 3, 4], 2), [[1, 2], [3, 4]])

    def test_uneven_split_puts_remainder_in_early_chunks(self) -> None:
        """Uneven distribution pushes extra items into the first workers."""
        chunks = split_into_chunks([1, 2, 3, 4, 5], 3)
        self.assertEqual(chunks, [[1, 2], [3, 4], [5]])

    def test_preserves_order_across_chunks(self) -> None:
        """Chunks are contiguous slices so concatenation restores the input."""
        items = list(range(17))
        chunks = split_into_chunks(items, 4)
        flattened: list[int] = []
        for chunk in chunks:
            flattened.extend(chunk)
        self.assertEqual(flattened, items)


if __name__ == "__main__":
    unittest.main()
