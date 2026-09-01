"""Unit tests for the ``order`` Typer subcommand (the biggest subcommand)."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.cli.typer_app import app


def test_order_help_lists_all_flag_groups() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["order", "--help"])
    assert result.exit_code == 0
    # Common args
    assert "--profile" in result.stdout
    assert "--config" in result.stdout
    # Runtime
    assert "--limit" in result.stdout
    assert "--debug-browser" in result.stdout
    assert "--resume" in result.stdout
    assert "--stop-flag" in result.stdout
    assert "--fast-search" in result.stdout
    assert "--match-only" in result.stdout
    assert "--execution-mode" in result.stdout
    # Risk
    assert "--matching-risk-policy" in result.stdout
    assert "--flagged-match-action" in result.stdout
    # Store filters
    assert "--warehouse-mode" in result.stdout
    assert "--min-discount-percent" in result.stdout
    assert "--prevented-items-excel" in result.stdout
    # Excel target source
    assert "--excel-target" in result.stdout
    assert "--all-excel-targets" in result.stdout
    assert "--excel-target-path" in result.stdout
    # Manual review
    assert "--from-manual-review-correc" in result.stdout  # truncated by Rich panel
    # Format
    assert "--format" in result.stdout


def test_order_invokes_handler_with_all_flag_groups() -> None:
    runner = CliRunner()
    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        get_cmd.return_value = lambda cfg, args: 0
        load_cfg.return_value = object()
        result = runner.invoke(
            app,
            [
                "order",
                "--excel", "data/input/order.xlsx",
                "--profile", "wardany",
                "--excel-target", "alnasr",
                "--match-only",
                "--execution-mode", "api",
                "--warehouse-mode", "max_discount",
                "--min-discount-percent", "10",
                "--format", "json",
            ],
        )

    assert result.exit_code == 0
    assert get_cmd.called
    assert get_cmd.call_args.args[0] == "order"


def test_order_accepts_all_excel_targets_flag() -> None:
    """The ``--all-excel-targets`` flag must be accepted by the CLI parser."""
    runner = CliRunner()
    captured: dict[str, object] = {}

    def _capture(cfg, args):
        captured["args"] = args
        return 0

    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        get_cmd.return_value = _capture
        load_cfg.return_value = object()
        result = runner.invoke(
            app,
            [
                "order",
                "--excel", "data/input/order.xlsx",
                "--all-excel-targets",
                "--match-only",
            ],
        )

    assert result.exit_code == 0
    handler_args = captured["args"]
    assert getattr(handler_args, "all_excel_targets", None) is True
