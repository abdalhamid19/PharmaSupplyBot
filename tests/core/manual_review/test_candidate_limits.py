from __future__ import annotations

import pytest

from src.core.manual_review.candidate_limits import normalize_candidate_limit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0, 1), (-4, 1), (None, 5), ("invalid", 5), ("7", 7), (12, 12)],
)
def test_candidate_limit_semantics_are_shared(raw, expected) -> None:
    assert normalize_candidate_limit(raw) == expected
