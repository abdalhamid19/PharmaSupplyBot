"""Materialize Typer parameters into the legacy CLI command namespace."""

from __future__ import annotations

from argparse import Namespace
from typing import Any

from typer import Context

from src.cli.cli_config import apply_preset, inject_defaults, load_user_config
from src.cli.cli_runner import ns_from_ctx


def build_command_arguments(ctx: Context, command_name: str) -> Namespace:
    """Build command arguments and apply user-configured defaults once."""
    arguments = ns_from_ctx(ctx, cmd=command_name)
    arguments._typer_defaults = _collect_defaults(ctx)
    user_config = load_user_config()
    arguments = apply_preset(
        None,
        arguments,
        getattr(arguments, "preset", None),
        user_config,
    )
    return inject_defaults(None, arguments, user_config)


def _collect_defaults(ctx: Context) -> dict[str, Any]:
    """Snapshot declared Typer defaults for user-config precedence checks."""
    command = ctx.command
    if command is None:
        return {}
    return {
        parameter.name: parameter.default
        for parameter in command.params
        if getattr(parameter, "name", None) is not None
    }


__all__ = ["build_command_arguments"]
