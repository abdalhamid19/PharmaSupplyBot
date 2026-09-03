"""Unit tests for the parser-agnostic ``_was_passed`` helper."""

from __future__ import annotations

from src.cli.cli_config import _was_passed


def test_was_passed_returns_false_when_current_equals_default() -> None:
    assert _was_passed("excel", "data.xlsx", "data.xlsx") is False


def test_was_passed_returns_true_when_current_differs_from_default() -> None:
    assert _was_passed("excel", "other.xlsx", "data.xlsx") is True


def test_was_passed_bool_flag_true_when_default_false() -> None:
    # store_true semantics: default=False, current=True → user passed it
    assert _was_passed("quiet", True, False) is True


def test_was_passed_bool_flag_false_when_default_false() -> None:
    assert _was_passed("quiet", False, False) is False


def test_was_passed_int_value_unchanged() -> None:
    assert _was_passed("limit", 0, 0) is False
    assert _was_passed("limit", 5, 0) is True


def test_was_passed_none_current_matches_none_default() -> None:
    assert _was_passed("excel", None, None) is False
