"""Unit tests for the Typer CLI application skeleton."""

from __future__ import annotations

from typer.testing import CliRunner

from src.cli.typer_app import app


def test_root_help_lists_global_logging_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--log-level" in result.stdout
    assert "--quiet" in result.stdout
    assert "--json-log-records" in result.stdout
    assert "--rich-logs" in result.stdout


def test_show_completion_bash_returns_nonempty_script() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["show-completion", "bash"])
    assert result.exit_code == 0
    assert len(result.stdout) > 50
    # Bash completion should mention "complete" or "comp"
    assert "complete" in result.stdout or "comp" in result.stdout


def test_show_completion_zsh_returns_nonempty_script() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["show-completion", "zsh"])
    assert result.exit_code == 0
    assert len(result.stdout) > 50


def test_show_completion_fish_returns_nonempty_script() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["show-completion", "fish"])
    assert result.exit_code == 0
    assert len(result.stdout) > 50


def test_show_completion_invalid_shell_exits_5() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["show-completion", "powershell"])
    # We map invalid shell → exit code 5 (validation error) per errors.py
    assert result.exit_code == 5


def test_no_args_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, [])
    # Typer's no_args_is_help=True prints help. In Typer 0.27 the exit
    # code is 2 (UsageError) when no subcommand is provided; we only
    # care that help was shown, not the exact code.
    assert "Tawreed" in result.stdout or "PharmaSupplyBot" in result.stdout
    assert "--log-level" in result.stdout
