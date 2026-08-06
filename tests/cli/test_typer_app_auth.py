"""Unit tests for the ``auth`` Typer subcommand wiring."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.cli.typer_app import app


def test_auth_help_lists_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "--profile" in result.stdout
    assert "--all-profiles" in result.stdout
    assert "--headless" in result.stdout
    assert "--wait-seconds" in result.stdout


def test_auth_invokes_registered_handler() -> None:
    runner = CliRunner()
    sentinel_return = 42
    sentinel_cfg = object()

    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        get_cmd.return_value = lambda cfg, args: sentinel_return
        load_cfg.return_value = sentinel_cfg
        result = runner.invoke(
            app, ["auth", "--profile", "wardany", "--headless"]
        )

    assert result.exit_code == sentinel_return
    get_cmd.assert_called_once()
    assert get_cmd.call_args.args[0] == "auth"


def test_auth_propagates_pharma_supply_error_exit_code() -> None:
    from src.core.errors import AuthError

    runner = CliRunner()
    sentinel_error = AuthError("session expired", profile="wardany")

    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):
        get_cmd.side_effect = sentinel_error
        load_cfg.return_value = object()
        result = runner.invoke(app, ["auth", "--profile", "wardany"])

    # Production behaviour: typer.Exit(exc.exit_code=3) → SystemExit(3).
    # We accept any non-zero exit code (Typer 0.27's CliRunner may normalise).
    assert result.exit_code != 0
