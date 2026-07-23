"""Unit tests for the output-format presenter."""

from __future__ import annotations

import json

import pytest

from src.cli.presenter import FormatFlags, render_table


def test_render_table_json_envelope_is_valid_json() -> None:
    rows = [{"name": "Panadol", "qty": 1}, {"name": "Devarol", "qty": 2}]
    fmt = FormatFlags(json=True, plain=False, no_color=True)
    out = render_table(rows, ["name", "qty"], fmt)
    parsed = json.loads(out)
    assert parsed["ok"] is True
    assert parsed["data"] == rows


def test_render_table_plain_is_tsv_with_header() -> None:
    rows = [{"name": "Panadol", "qty": 1}]
    fmt = FormatFlags(json=False, plain=True, no_color=True)
    out = render_table(rows, ["name", "qty"], fmt)
    lines = out.split("\n")
    assert lines[0] == "name\tqty"
    assert lines[1] == "Panadol\t1"


def test_render_table_human_renders_rich_table() -> None:
    rows = [{"name": "Panadol", "qty": 1}]
    fmt = FormatFlags(json=False, plain=False, no_color=True)
    out = render_table(rows, ["name", "qty"], fmt)
    # Rich-rendered table contains the values; without color codes when no_color
    assert "Panadol" in out
    assert "1" in out


def test_format_flags_resolve_explicit_json_overrides_auto() -> None:
    fmt = FormatFlags.resolve(explicit="json")
    assert fmt.json is True
    assert fmt.plain is False
    assert fmt.no_color is True


def test_format_flags_resolve_explicit_plain_overrides_auto() -> None:
    fmt = FormatFlags.resolve(explicit="plain")
    assert fmt.json is False
    assert fmt.plain is True
    assert fmt.no_color is True


def test_format_flags_resolve_explicit_human_keeps_color() -> None:
    fmt = FormatFlags.resolve(explicit="human")
    assert fmt.json is False
    assert fmt.plain is False
    assert fmt.no_color is False


def test_format_flags_resolve_auto_plain_when_stdout_is_piped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    fmt = FormatFlags.resolve(explicit=None)
    assert fmt.plain is True
    assert fmt.no_color is True
    assert fmt.json is False


def test_format_flags_resolve_auto_human_when_stdout_is_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    fmt = FormatFlags.resolve(explicit=None)
    assert fmt.json is False
    assert fmt.plain is False
    assert fmt.no_color is False


def test_render_table_handles_missing_keys_in_json() -> None:
    rows = [{"name": "Panadol"}, {"name": "Devarol", "qty": 3}]
    fmt = FormatFlags(json=True, plain=False, no_color=True)
    out = render_table(rows, ["name", "qty"], fmt)
    parsed = json.loads(out)
    # JSON envelope: missing keys are simply absent (passthrough, no padding).
    assert "qty" not in parsed["data"][0]
    assert parsed["data"][1]["qty"] == 3


def test_render_table_handles_missing_keys_in_plain() -> None:
    rows = [{"name": "Panadol"}, {"name": "Devarol", "qty": 3}]
    fmt = FormatFlags(json=False, plain=True, no_color=True)
    out = render_table(rows, ["name", "qty"], fmt)
    lines = out.split("\n")
    # Plain TSV always emits a column for every requested column.
    assert lines[0] == "name\tqty"
    assert lines[1] == "Panadol\t"
    assert lines[2] == "Devarol\t3"


def test_render_table_empty_rows_returns_envelope() -> None:
    fmt = FormatFlags(json=True, plain=False, no_color=True)
    out = render_table([], ["name", "qty"], fmt)
    parsed = json.loads(out)
    assert parsed["ok"] is True
    assert parsed["data"] == []
