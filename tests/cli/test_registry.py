"""Tests for the command registry."""

from __future__ import annotations

from src.cli.registry import COMMANDS, get_command, register


def test_register_adds_to_dict() -> None:
    @register("test.adds")
    def cmd(app_config, args) -> int:  # pragma: no cover - body not called
        return 0

    try:
        assert "test.adds" in COMMANDS
        assert COMMANDS["test.adds"] is cmd
    finally:
        # تنظيف لتجنب تسريب decorator state بين الاختبارات
        COMMANDS.pop("test.adds", None)


def test_register_raises_on_duplicate_name() -> None:
    @register("test.dup")
    def cmd1(app_config, args) -> int:  # pragma: no cover
        return 0

    try:
        with pytest_raises(ValueError, match="already registered"):
            @register("test.dup")
            def cmd2(app_config, args) -> int:  # pragma: no cover
                return 1
    finally:
        COMMANDS.pop("test.dup", None)


def test_get_command_returns_registered_callable() -> None:
    @register("test.get")
    def cmd(app_config, args) -> int:  # pragma: no cover
        return 7

    try:
        assert get_command("test.get") is cmd
    finally:
        COMMANDS.pop("test.get", None)


def test_get_command_raises_lookup_error_with_helpful_message() -> None:
    with pytest_raises(LookupError, match="Unknown command 'nope'"):
        get_command("nope")


# helper محلّي لتفادي import زائد في أعلى الملف
def pytest_raises(exc_type, match=None):
    import pytest
    return pytest.raises(exc_type, match=match)


# ─────────────────────────── Real CLI commands ───────────────────────────


def test_real_cli_commands_are_registered() -> None:
    """The five production subcommands must be present in the registry."""
    # Import the module so the @register decorators fire
    from src.cli import cli_commands  # noqa: F401

    expected = {"auth", "order", "remove-cart", "export-products", "match-products"}
    missing = expected - set(COMMANDS)
    assert not missing, f"missing commands in registry: {missing}"