"""Typer + Rich CLI application for PharmaSupplyBot.

Five subcommands (registered incrementally in Tasks 6-10):
``auth``, ``order``, ``remove-cart``, ``export-products``, ``match-products``.

Each subcommand is a thin adapter that:

1. Calls :func:`src.cli.cli_runner.ns_from_ctx` to build an
   ``argparse.Namespace`` from the parsed Typer context.
2. Loads the config and applies presets / defaults.
3. Dispatches to the registered command in :mod:`src.cli.registry`.

The hand-rolled ``argparse`` parsers under ``src/cli/parsers/`` will
be removed in Task 14 once all subcommands are wired through here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer
from typer import Context

# Importing cli_commands has the side-effect of populating the command registry.
from src.cli import cli_commands  # noqa: F401
from src.cli.cli_runner import ns_from_ctx
from src.cli.cli_config import apply_preset, inject_defaults
from src.cli.logging_setup import LoggingConfig, configure_logging
from src.cli.registry import get_command
from src.core.config.config import load_config
from src.core.errors import PharmaSupplyError


logger = logging.getLogger(__name__)


app = typer.Typer(
    name="pharmabot",
    help="Tawreed authentication, ordering, and exports CLI.",
    rich_markup_mode="rich",
    add_completion=False,  # we ship our own via `show-completion`
    no_args_is_help=True,
)


# ─────────────────────────── Global options ───────────────────────────


@app.callback()
def _root(
    ctx: Context,
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        envvar="PHARMABOT_LOG_LEVEL",
        help="Minimum log level emitted to console (DEBUG/INFO/WARNING/ERROR/CRITICAL).",
    ),
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress non-error console output."
    ),
    json_logs: bool = typer.Option(
        False,
        "--json-log-records",
        help="Emit log records as JSON (one object per line). Renamed from --json-logs.",
    ),
    rich_logs: bool = typer.Option(
        False,
        "--rich-logs",
        help="Route console log records through RichHandler for colourised output.",
    ),
) -> None:
    """Global logging + output options applied before any subcommand runs."""
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["quiet"] = quiet
    ctx.obj["json_logs"] = json_logs
    ctx.obj["rich_logs"] = rich_logs


# ─────────────────────────── Hidden: shell-completion ──────────────────


@app.command("show-completion", hidden=True)
def show_completion(
    shell: str = typer.Argument(
        ..., help="Target shell: bash, zsh, or fish."
    )
) -> None:
    """Emit a shell-completion script for the given shell."""
    from typer.completion import get_completion_script

    if shell not in ("bash", "zsh", "fish"):
        typer.echo(
            f"Unknown shell '{shell}'. Supported: bash, zsh, fish.",
            err=True,
        )
        raise typer.Exit(5)
    # ``complete_var`` is the env var name read by the shell script.
    # Typer's convention: ``_TYPER_COMPLETE`` for bash/zsh, ``_FISH_COMPLETE`` for fish.
    complete_var = "_FISH_COMPLETE" if shell == "fish" else "_TYPER_COMPLETE"
    script = get_completion_script(
        shell=shell, prog_name="pharmabot", complete_var=complete_var
    )
    typer.echo(script)


# ─────────────────────────── Generic subcommand wrapper ────────────────


def _run_registered(ctx: Context, cmd_name: str) -> int:
    """Common entry-point for every subcommand.

    Sequence:
    1. Configure logging from the top-level options.
    2. Build a flat ``argparse.Namespace`` from the Typer context.
    3. Apply user-config precedence: preset < defaults < CLI args.
    4. Load :class:`AppConfig` and dispatch to the registered handler.

    Any :class:`PharmaSupplyError` is mapped to its ``exit_code`` and
    reported on stderr; anything else becomes exit code 99.
    """
    obj = ctx.obj or {}

    # 1. Logging (idempotent — safe to call multiple times).
    configure_logging(
        LoggingConfig(
            level=obj.get("log_level", "INFO"),
            quiet=bool(obj.get("quiet", False)),
            json_logs=bool(obj.get("json_logs", False)),
        )
    )

    # 2. Materialise the legacy Namespace.
    ns = ns_from_ctx(ctx, cmd=cmd_name)
    ns._typer_defaults = _collect_defaults(ctx)

    # 3. Apply user-config precedence (CLI > preset > defaults).
    ns = apply_preset(None, ns, getattr(ns, "preset", None))  # type: ignore[arg-type]
    ns = inject_defaults(None, ns)  # type: ignore[arg-type]

    # 4. Load config + dispatch.
    config_path = Path(getattr(ns, "config", "config.yaml"))
    app_config = load_config(config_path)
    command = get_command(cmd_name)
    try:
        return command(app_config, ns)
    except PharmaSupplyError as exc:
        typer.echo(f"{exc}", err=True)
        raise typer.Exit(exc.exit_code)
    except Exception:
        logger.exception("unhandled exception in command %s", cmd_name)
        raise typer.Exit(99)


def _collect_defaults(ctx: Context) -> dict[str, Any]:
    """Snapshot the declared parameter defaults for ``_was_passed`` to consult."""
    defaults: dict[str, Any] = {}
    cmd = ctx.command
    if cmd is None:
        return defaults
    for param in cmd.params:
        name = getattr(param, "name", None)
        if name is not None:
            defaults[name] = param.default
    return defaults


# ─────────────────────────── One stub subcommand (auth) ────────────────


@app.command("auth")
def auth_cmd(
    ctx: Context,
    profile: str | None = typer.Option(None, "--profile", help="Single profile key."),
    all_profiles: bool = typer.Option(False, "--all-profiles", help="All profiles."),
    headless: bool = typer.Option(False, "--headless", help="Run browser headless."),
    wait_seconds: int = typer.Option(30, "--wait-seconds", help="2FA wait time."),
) -> None:
    """Authenticate and persist session state for the selected profiles.

    [STUB — Task 5] The handler is wired in Task 6.
    """
    # For now, just confirm the stub is reachable and the options were parsed.
    typer.echo(f"auth stub: profile={profile} headless={headless}")
    raise typer.Exit(0)


# Re-export for downstream imports
__all__ = ["app"]
