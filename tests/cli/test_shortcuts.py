"""Tests for the CLI shortcut aliases (-x, -n, -p, -c).

These tests build a fresh parser via :func:`build_parser` and assert
that the new short flags are accepted everywhere the long flags
were accepted. The point is twofold:

1. The shortcuts actually wire up to the right destinations.
2. Long flags still work unchanged (backward compatibility).

Why no fake monkey-patching of the global config? Because the only
thing we're testing here is argparse — no config loading, no
presets. We invoke ``parser.parse_args`` directly.
"""

from __future__ import annotations

import pytest

from src.cli.parsers.cli_parser import build_parser


# ─────────────────────────── -x / --excel ────────────────────────────


def test_order_accepts_x_shortcut_for_excel() -> None:
    parser = build_parser()
    args = parser.parse_args(["order", "-x", "data/x.xlsx"])
    assert args.excel == "data/x.xlsx"
    assert args.cmd == "order"


def test_remove_cart_accepts_x_shortcut_for_excel() -> None:
    parser = build_parser()
    args = parser.parse_args(["remove-cart", "-x", "data/r.xlsx"])
    assert args.excel == "data/r.xlsx"
    assert args.cmd == "remove-cart"


def test_match_products_accepts_x_shortcut_for_excel() -> None:
    parser = build_parser()
    args = parser.parse_args(["match-products", "-x", "inv.xlsx"])
    assert args.excel == "inv.xlsx"
    assert args.cmd == "match-products"


def test_order_long_form_excel_still_works() -> None:
    """Backward compatibility: --excel must keep working as before."""
    parser = build_parser()
    args = parser.parse_args(["order", "--excel", "data/x.xlsx"])
    assert args.excel == "data/x.xlsx"


def test_match_products_long_form_excel_still_works() -> None:
    parser = build_parser()
    args = parser.parse_args(["match-products", "--excel", "inv.xlsx"])
    assert args.excel == "inv.xlsx"


# ─────────────────────────── -n / --limit ───────────────────────────


def test_order_accepts_n_shortcut_for_limit() -> None:
    parser = build_parser()
    args = parser.parse_args(["order", "-n", "20"])
    assert args.limit == 20


def test_match_products_accepts_n_shortcut_for_limit() -> None:
    parser = build_parser()
    args = parser.parse_args(["match-products", "-x", "inv.xlsx", "-n", "5"])
    assert args.limit == 5
    assert args.excel == "inv.xlsx"


def test_export_products_accepts_n_shortcut_for_limit() -> None:
    parser = build_parser()
    args = parser.parse_args(["export-products", "-n", "100"])
    assert args.limit == 100


def test_order_long_form_limit_still_works() -> None:
    parser = build_parser()
    args = parser.parse_args(["order", "--limit", "30"])
    assert args.limit == 30


def test_export_long_form_limit_still_works() -> None:
    parser = build_parser()
    args = parser.parse_args(["export-products", "--limit", "50"])
    assert args.limit == 50


# ─────────────────────────── -p / -c (regression — already in 1b) ─────


def test_order_accepts_p_shortcut_for_profile() -> None:
    parser = build_parser()
    args = parser.parse_args(["order", "-p", "wardany"])
    assert args.profile == "wardany"


def test_order_accepts_c_shortcut_for_config() -> None:
    parser = build_parser()
    args = parser.parse_args(["order", "-c", "my-config.yaml"])
    assert args.config == "my-config.yaml"


def test_long_form_profile_and_config_still_work() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["order", "--profile", "pharm1", "--config", "x.yaml"]
    )
    assert args.profile == "pharm1"
    assert args.config == "x.yaml"


# ─────────────────────────── Combined usage ──────────────────────────


def test_realistic_command_line_with_all_shortcuts() -> None:
    """The whole point: realistic command line should be much shorter."""
    parser = build_parser()
    args = parser.parse_args(
        [
            "order",
            "-p", "wardany",       # was --profile wardany
            "-c", "state/cfg.yaml",  # was --config state/cfg.yaml
            "-x", "data/inv.xlsx",   # was --excel data/inv.xlsx
            "-n", "20",              # was --limit 20
            "--match-only",
        ]
    )
    assert args.profile == "wardany"
    assert args.config == "state/cfg.yaml"
    assert args.excel == "data/inv.xlsx"
    assert args.limit == 20
    assert args.match_only is True


def test_short_and_long_can_be_mixed() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["order", "-p", "wardany", "--excel", "x.xlsx", "-n", "10"]
    )
    assert args.profile == "wardany"
    assert args.excel == "x.xlsx"
    assert args.limit == 10


# ─────────────────────────── Conflict / safety checks ───────────────


def test_x_does_not_collide_with_any_long_flag() -> None:
    """Sanity: -x must not be a prefix of any other flag's first char."""
    # If someone added a --xml flag, argparse would error at build_parser
    # time. We just confirm -x is now reserved.
    parser = build_parser()
    # Should not raise
    parser.parse_args(["order", "-x", "xlsx"])


def test_n_does_not_collide() -> None:
    parser = build_parser()
    # -n could in theory clash with --no-... flags, but the project
    # has none. Smoke test only.
    parser.parse_args(["order", "-n", "5"])
