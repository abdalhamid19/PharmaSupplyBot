"""Unit tests for the ``remove-cart`` Typer subcommand."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.cli.typer_app import app


def test_remove_cart_help_lists_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["remove-cart", "--help"])
    assert result.exit_code == 0
    assert "--excel" in result.stdout
    assert "--debug-browser" in result.stdout
    assert "--stop-flag" in result.stdout
    assert "--execution-mode" in result.stdout
    assert "--limit" in result.stdout
    assert "--from-manual-review" in result.stdout
    assert "--manual-review-scope" in result.stdout
    assert "--format" in result.stdout


def test_remove_cart_invokes_handler() -> None:
    runner = CliRunner()
    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        get_cmd.return_value = lambda cfg, args: 0
        load_cfg.return_value = object()
        result = runner.invoke(
            app,
            ["remove-cart", "--excel", "data.xlsx", "--profile", "wardany"],
        )

    assert result.exit_code == 0
    assert get_cmd.called
    assert get_cmd.call_args.args[0] == "remove-cart"


def test_remove_cart_forwards_limit() -> None:
    runner = CliRunner()
    captured: dict[str, int | None] = {"limit": None}
    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        def handler(_cfg, args):
            captured["limit"] = args.limit
            return 0

        get_cmd.return_value = handler
        load_cfg.return_value = object()
        result = runner.invoke(
            app,
            [
                "remove-cart",
                "--excel", "data.xlsx",
                "--profile", "wardany",
                "--limit", "30",
            ],
        )

    assert result.exit_code == 0
    assert captured["limit"] == 30
