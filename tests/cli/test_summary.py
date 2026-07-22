"""Tests for the structured command-summary helper.

The helper :func:`print_command_summary` is the single visual contract
for every CLI subcommand's terminal output. It is a pure I/O function
that must:

  * Print ``✅ <cmd> completed`` on success.
  * Print ``❌ <cmd> failed`` on failure (and write to stderr).
  * Be hidden entirely under ``--quiet``.
  * Render common field types (Path, int, float, list, bool, None)
    in a terminal-friendly form.
  * Never raise on weird inputs (a typo in a field name from a
    caller should not crash the CLI).

We exercise all of those, plus the duration formatter and the
:class:`CommandTimer`.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.cli.cli_shared import (
    CommandTimer,
    _render_field,
    format_duration,
    is_quiet,
    print_command_summary,
)


# ─────────────────────────── format_duration ────────────────────────


def test_format_duration_none_returns_dash() -> None:
    assert format_duration(None) == "-"


def test_format_duration_zero() -> None:
    assert format_duration(0) == "0s"


def test_format_duration_under_minute() -> None:
    assert format_duration(42) == "42s"


def test_format_duration_minutes_and_seconds() -> None:
    assert format_duration(125) == "2m 05s"


def test_format_duration_hours() -> None:
    assert format_duration(3725) == "1h 02m"


def test_format_duration_clamps_negative_to_zero() -> None:
    # Defensive: monotonic time should never go backwards, but if a
    # caller hands us -1 (e.g. as a sentinel), we don't crash.
    assert format_duration(-5) == "0s"


def test_format_duration_accepts_float() -> None:
    # Truncates to int — we don't show "3.7s".
    assert format_duration(3.7) == "3s"


# ─────────────────────────── _render_field ──────────────────────────


def test_render_field_none() -> None:
    assert _render_field(None) == "-"


def test_render_field_path_uses_str() -> None:
    p = Path("/tmp/foo/bar.csv")
    assert _render_field(p) == str(p)


def test_render_field_bool_to_yes_no() -> None:
    assert _render_field(True) == "yes"
    assert _render_field(False) == "no"


def test_render_field_float_trims_trailing_zeros() -> None:
    assert _render_field(0.9) == "0.9"
    assert _render_field(0.95) == "0.95"
    # Don't render scientific notation for normal percentages.
    assert _render_field(89.0) == "89"


def test_render_field_short_list() -> None:
    assert _render_field(["a", "b"]) == "[a, b]"
    assert _render_field(["a", "b", "c"]) == "[a, b, c]"


def test_render_field_long_list_collapsed() -> None:
    rendered = _render_field(list(range(20)))
    assert "20 items" in rendered
    assert rendered.startswith("[")


def test_render_field_str_passes_through() -> None:
    assert _render_field("hello") == "hello"


# ─────────────────────────── print_command_summary ──────────────────


def test_summary_success_writes_to_stdout(capsys) -> None:
    print_command_summary("order", {"processed": 18, "matched": 16})
    out, err = capsys.readouterr()
    assert "✅ order completed" in out
    assert err == ""


def test_summary_failure_writes_to_stderr(capsys) -> None:
    print_command_summary("order", {"processed": 0}, success=False)
    out, err = capsys.readouterr()
    assert "❌ order failed" in err
    assert "✅" not in out
    assert "✅" not in err


def test_summary_quiet_silent_on_stdout_and_stderr(capsys) -> None:
    print_command_summary("order", {"x": 1}, quiet=True)
    out, err = capsys.readouterr()
    assert out == "" and err == ""


def test_summary_failure_quiet_still_silent(capsys) -> None:
    # quiet wins over success/failure (cron safety first)
    print_command_summary("order", {}, success=False, quiet=True)
    out, err = capsys.readouterr()
    assert out == "" and err == ""


def test_summary_with_no_fields_just_prints_header(capsys) -> None:
    print_command_summary("auth")
    out, err = capsys.readouterr()
    assert out.strip() == "✅ auth completed"


def test_summary_with_none_fields_works(capsys) -> None:
    print_command_summary("order", {"processed": None, "matched": 5})
    out, _ = capsys.readouterr()
    # Padding is 12 chars wide; values follow a single space.
    assert "   - processed    -" in out
    assert "   - matched      5" in out


def test_summary_values_are_left_aligned(capsys) -> None:
    print_command_summary("order", {"x": 1, "longer_key": 2})
    out, _ = capsys.readouterr()
    # Both rows use the same 12-char padded field for the label,
    # followed by a single space and the value. So 'x' (1 char) is
    # followed by 11 spaces, 'longer_key' (10 chars) by 2 spaces.
    assert "   - x            1" in out
    assert "   - longer_key   2" in out
    # And the gap between label and value is wider for 'x'.
    x_gap = out.split("   - x")[1].split("1")[0]
    longer_gap = out.split("   - longer_key")[1].split("2")[0]
    assert len(x_gap) > len(longer_gap)


def test_summary_with_path(capsys) -> None:
    """Path objects render via str() — cross-platform-safe."""
    p = Path("order_summary.csv").resolve()
    print_command_summary("order", {"summary": p})
    out, _ = capsys.readouterr()
    assert "order_summary.csv" in out  # path-like contents, OS-agnostic


def test_summary_with_duration_string(capsys) -> None:
    print_command_summary("order", {"duration": format_duration(125)})
    out, _ = capsys.readouterr()
    assert "2m 05s" in out


def test_summary_never_raises_on_unknown_types(capsys) -> None:
    """A weird value type shouldn't crash the CLI."""
    class Weird:
        def __str__(self) -> str:
            return "<weird>"

    print_command_summary("order", {"weird": Weird()})
    out, _ = capsys.readouterr()
    assert "<weird>" in out


def test_summary_handles_empty_fields_dict(capsys) -> None:
    print_command_summary("order", {})
    out, _ = capsys.readouterr()
    assert out.strip() == "✅ order completed"


# ─────────────────────────── CommandTimer ───────────────────────────


def test_command_timer_measures_elapsed_time() -> None:
    import time

    timer = CommandTimer()
    assert timer.seconds == 0.0
    with timer:
        time.sleep(0.05)
    assert timer.seconds >= 0.04  # allow clock slack
    assert timer.seconds < 1.0   # sanity


def test_command_timer_without_with_block_stays_zero() -> None:
    timer = CommandTimer()
    # Not used as a context manager → no time recorded.
    assert timer.seconds == 0.0


# ─────────────────────────── is_quiet ───────────────────────────────


def test_is_quiet_true_when_attribute_set() -> None:
    args = SimpleNamespace(quiet=True)
    assert is_quiet(args) is True


def test_is_quiet_false_when_attribute_set_false() -> None:
    args = SimpleNamespace(quiet=False)
    assert is_quiet(args) is False


def test_is_quiet_false_when_attribute_missing() -> None:
    """A test double or older code path that lacks --quiet must not
    raise — we treat missing as 'not quiet'."""
    args = SimpleNamespace()
    assert is_quiet(args) is False


def test_is_quiet_accepts_plain_object() -> None:
    """The function's type hint says ``object``; verify tolerance."""
    assert is_quiet(object()) is False  # no quiet attribute → False


# ─────────────────────────── Integration smoke ──────────────────────


def test_summary_format_for_each_subcommand() -> None:
    """Every subcommand produces the same header shape regardless of fields."""
    for cmd in ("auth", "order", "remove-cart", "export-products", "match-products"):
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            print_command_summary(cmd, {"duration": "0s"})
        out = buf.getvalue()
        assert f"✅ {cmd} completed" in out
        assert "   - duration     0s" in out


def test_realistic_order_summary(capsys) -> None:
    """A realistic summary block matches the documented format."""
    print_command_summary(
        "order",
        {
            "processed": 20,
            "matched": 18,
            "flagged": 2,
            "duration": format_duration(134),
            "summary": Path("artifacts/wardany/order_summary.csv"),
        },
    )
    out, _ = capsys.readouterr()
    assert "✅ order completed" in out
    assert "   - processed    20" in out
    assert "   - matched      18" in out
    assert "   - flagged      2" in out
    assert "   - duration     2m 14s" in out
    assert "   - summary      " in out
    assert "order_summary.csv" in out