"""Unit tests for the ``export-products`` Typer subcommand."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.cli.typer_app import app


def test_export_products_help_lists_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["export-products", "--help"])
    assert result.exit_code == 0
    assert "--profile" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--stem" in result.stdout
    assert "--page-size" in result.stdout
    assert "--limit" in result.stdout
    assert "--debug-browser" in result.stdout
    assert "--format" in result.stdout  # new Rich-format flag


def test_export_products_invokes_registered_handler() -> None:
    runner = CliRunner()
    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        get_cmd.return_value = lambda cfg, args: 0
        load_cfg.return_value = object()
        result = runner.invoke(
            app,
            [
                "export-products",
                "--profile", "wardany",
                "--stem", "products_v2",
                "--page-size", "50",
                "--format", "json",
            ],
        )

    assert result.exit_code == 0
    assert get_cmd.called
    assert get_cmd.call_args.args[0] == "export-products"


def test_export_products_default_format_is_human() -> None:
    runner = CliRunner()
    captured_args = {}

    def fake_handler(cfg, args):
        captured_args["format"] = getattr(args, "format", None)
        return 0

    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        get_cmd.return_value = fake_handler
        load_cfg.return_value = object()
        runner.invoke(app, ["export-products", "--profile", "wardany"])

    assert captured_args["format"] is None  # None means auto-detect
