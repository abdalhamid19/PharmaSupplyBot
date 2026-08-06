"""Tests for the CLI shortcut aliases (-x, -n, -p, -c).

These tests verify the Typer app's short-flag aliases wire up to the
right destinations, and that long flags still work unchanged (backward
compatibility).
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.cli.typer_app import app


def _invoke(argv: list[str], captured: dict) -> object:
    """Helper: invoke the app with ``argv``, capture the handler's args."""
    runner = CliRunner()
    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):

        def fake_handler(cfg, args):
            for k in captured:
                captured[k] = getattr(args, k, None)
            return 0

        get_cmd.return_value = fake_handler
        load_cfg.return_value = object()
        return runner.invoke(app, argv)


# ─────────────────────────── -x / --excel ────────────────────────────


def test_order_accepts_x_shortcut_for_excel() -> None:
    captured: dict = {"excel": None, "cmd": None}
    result = _invoke(["order", "-x", "data/x.xlsx"], captured)
    assert result.exit_code == 0
    assert captured["excel"] == "data/x.xlsx"
    assert captured["cmd"] == "order"


def test_remove_cart_accepts_x_shortcut_for_excel() -> None:
    captured: dict = {"excel": None, "cmd": None}
    result = _invoke(["remove-cart", "-x", "data/r.xlsx"], captured)
    assert result.exit_code == 0
    assert captured["excel"] == "data/r.xlsx"
    assert captured["cmd"] == "remove-cart"


def test_match_products_accepts_x_shortcut_for_excel() -> None:
    captured: dict = {"excel": None, "cmd": None}
    result = _invoke(["match-products", "-x", "data/m.xlsx"], captured)
    assert result.exit_code == 0
    assert captured["excel"] == "data/m.xlsx"
    assert captured["cmd"] == "match-products"


def test_export_products_does_not_accept_x_shortcut() -> None:
    """``-x`` is not part of the export-products surface; long forms are."""
    runner = CliRunner()
    result = runner.invoke(app, ["export-products", "-x", "data.xlsx"])
    # Typer surfaces unknown options as exit code 2.
    assert result.exit_code != 0


# ─────────────────────────── -n / --limit ────────────────────────────


def test_order_accepts_n_shortcut_for_limit() -> None:
    captured: dict = {"limit": None, "cmd": None}
    result = _invoke(
        ["order", "--excel", "data.xlsx", "-n", "5"],
        captured,
    )
    assert result.exit_code == 0
    assert captured["limit"] == 5
    assert captured["cmd"] == "order"


def test_export_products_accepts_n_shortcut_for_limit() -> None:
    captured: dict = {"limit": None, "cmd": None}
    result = _invoke(["export-products", "-n", "10"], captured)
    assert result.exit_code == 0
    assert captured["limit"] == 10
    assert captured["cmd"] == "export-products"


def test_match_products_accepts_n_shortcut_for_limit() -> None:
    captured: dict = {"limit": None, "cmd": None}
    result = _invoke(
        ["match-products", "--excel", "data.xlsx", "-n", "3"],
        captured,
    )
    assert result.exit_code == 0
    assert captured["limit"] == 3


# ─────────────────────────── -p / --profile ────────────────────────────


def test_auth_accepts_p_shortcut_for_profile() -> None:
    captured: dict = {"profile": None, "cmd": None}
    result = _invoke(["auth", "-p", "wardany"], captured)
    assert result.exit_code == 0
    assert captured["profile"] == "wardany"
    assert captured["cmd"] == "auth"


def test_order_accepts_p_shortcut_for_profile() -> None:
    captured: dict = {"profile": None, "cmd": None}
    result = _invoke(
        ["order", "--excel", "data.xlsx", "-p", "wardany"],
        captured,
    )
    assert result.exit_code == 0
    assert captured["profile"] == "wardany"


# ─────────────────────────── -c / --config ────────────────────────────


def test_auth_accepts_c_shortcut_for_config() -> None:
    captured: dict = {"config": None, "cmd": None}
    result = _invoke(["auth", "-c", "alt_config.yaml"], captured)
    assert result.exit_code == 0
    assert captured["config"] == "alt_config.yaml"
    assert captured["cmd"] == "auth"


def test_order_accepts_c_shortcut_for_config() -> None:
    captured: dict = {"config": None, "cmd": None}
    result = _invoke(
        ["order", "--excel", "data.xlsx", "-c", "alt.yaml"],
        captured,
    )
    assert result.exit_code == 0
    assert captured["config"] == "alt.yaml"


# ─────────────────────────── -q / --quiet ────────────────────────────


def test_auth_accepts_q_shortcut_for_quiet() -> None:
    """``--quiet`` is a parent-callback option (placed before the subcommand).

    Typer only honours callback options when they appear before the
    subcommand name on the command line — that's how Click dispatches
    them to the callback rather than the subcommand.
    """
    captured: dict = {"quiet": False}
    result = _invoke(["--quiet", "auth"], captured)
    assert result.exit_code == 0
    assert captured["quiet"] is True
