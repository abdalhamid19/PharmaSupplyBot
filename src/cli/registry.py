"""Lightweight command registry for the Tawreed CLI.

Commands are plain callables decorated with :func:`register`. The runner
in ``run.py`` looks them up by the subparser name (``args.cmd``), which
means adding a new command is a one-line change with no edits to
``run.py``.

The signature contract for a registered command is:

    run_xxx_command(app_config: AppConfig, args: argparse.Namespace) -> int

The callable must return an integer exit code (0 = success).

A ``COMMANDS`` dictionary is exposed so tests and tooling can introspect
the available subcommands without re-parsing ``cli_parser``.
"""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.config.config_models import AppConfig


CommandFn = Callable[["AppConfig", Namespace], int]

# Public name → callable lookup. Populated by @register decorators below.
COMMANDS: dict[str, CommandFn] = {}


def register(name: str) -> Callable[[CommandFn], CommandFn]:
    """Decorator that registers a function under the given subcommand name.

    Usage::

        @register("auth")
        def run_auth_command(app_config, args) -> int:
            ...

    Raises ``ValueError`` on duplicate registration so we fail loudly
    during import rather than silently shadowing a command.
    """

    def decorator(fn: CommandFn) -> CommandFn:
        if name in COMMANDS:
            raise ValueError(
                f"Command '{name}' already registered by "
                f"{COMMANDS[name].__module__}.{COMMANDS[name].__name__}; "
                f"cannot also register {fn.__module__}.{fn.__name__}."
            )
        COMMANDS[name] = fn
        return fn

    return decorator


def get_command(name: str) -> CommandFn:
    """Look up a registered command by name.

    Raises ``LookupError`` with a helpful message if the command is
    unknown (so the CLI can map this to ``ValidationError`` /
    exit code 5).
    """

    try:
        return COMMANDS[name]
    except KeyError as exc:
        available = ", ".join(sorted(COMMANDS)) or "(none registered)"
        raise LookupError(
            f"Unknown command '{name}'. Available: {available}"
        ) from exc


__all__ = ["COMMANDS", "CommandFn", "register", "get_command"]