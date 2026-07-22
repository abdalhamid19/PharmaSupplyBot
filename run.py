"""CLI entry point for Tawreed authentication, ordering, and exports.

This module is intentionally tiny: it parses arguments, loads the
configuration, looks the requested subcommand up in the :mod:`registry`,
and lets the registered handler do the actual work.

Exit code conventions are documented in :mod:`src.core.errors`. The
catch-all at the bottom of :func:`main` ensures unexpected exceptions
still produce a structured exit code (``99``) instead of a raw traceback.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.cli import cli_commands  # noqa: F401  (side-effect: populates registry)
from src.cli.cli_commands import (
    run_auth_command,
    run_export_products_command,
    run_match_products_command,
    run_order_command,
    run_remove_cart_command,
)
from src.cli.cli_config import (
    GLOBAL_CONFIG_PATH,
    LOCAL_CONFIG_PATH,
    apply_preset,
    describe_sources,
    inject_defaults,
)
from src.cli.logging_setup import LoggingConfig, configure_logging
from src.cli.parsers.cli_parser import build_parser
from src.cli.registry import get_command
from src.core.config.config import load_config
from src.core.errors import PharmaSupplyError, ValidationError


def _resolve_logging_config(args) -> LoggingConfig:
    """Translate argparse flags into a :class:`LoggingConfig`.

    Supports the optional ``--log-level``, ``--quiet`` and
    ``--json-logs`` flags documented in ``docs/logging_system.md``.
    Falls back to sensible defaults when the flags are absent (e.g.
    when ``run.py`` is invoked from tests).
    """
    return LoggingConfig(
        level=getattr(args, "log_level", "INFO") or "INFO",
        quiet=bool(getattr(args, "quiet", False)),
        json_logs=bool(getattr(args, "json_logs", False)),
    )


def main() -> int:
    """Run the CLI command requested by the user."""
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    # Handle meta-flags first, before any logging/config setup. They
    # are pure side-effects (print to stdout, exit) and must not
    # require a config file or any other state.
    if getattr(args, "show_completion", None):
        from src.cli.completion import SUPPORTED_SHELLS, emit_completion

        try:
            print(emit_completion(args.show_completion))
            return 0
        except ValueError as exc:
            print(
                f"error: {exc}\n"
                f"supported shells: {', '.join(SUPPORTED_SHELLS)}",
                file=sys.stderr,
            )
            return 5  # ValidationError exit code

    # ✨ Initialize logging BEFORE running the command so every module
    # that grabs a logger at import time sees the configured handlers.
    configure_logging(_resolve_logging_config(args))
    logger = logging.getLogger(__name__)

    # ✨ Log user-config sources (once per run, at INFO so it's visible
    # without --log-level DEBUG). Quiet mode suppresses this so cron
    # logs stay clean.
    if not getattr(args, "quiet", False):
        sources = describe_sources()
        loaded = [
            p for p, exists in (
                (str(GLOBAL_CONFIG_PATH), sources["global_exists"]),
                (str(LOCAL_CONFIG_PATH.resolve()) if LOCAL_CONFIG_PATH.exists() else None, sources["local_exists"]),
            ) if exists
        ]
        if loaded:
            logger.info("user config loaded from: %s", ", ".join(loaded))

    if not getattr(args, "cmd", None):
        # No subcommand and no --show-completion → show help and exit
        # with the standard "user error" code.
        parser.print_help(sys.stderr)
        return 5

    try:
        # Preset first, then defaults, then explicit CLI args win.
        # This three-step merge implements the documented precedence:
        #   CLI args > --preset > ./.pharmabotrc > ~/.pharmabotrc > built-in defaults
        args = apply_preset(parser, args, getattr(args, "preset", None))
        args = inject_defaults(parser, args)

        config_path = Path(args.config)
        app_config = load_config(config_path)
        command = get_command(args.cmd)
        logger.debug(
            "dispatching command",
            extra={"cmd": args.cmd, "config": str(config_path)},
        )
        return command(app_config, args)
    except ValueError as error:
        # Preset-related failures (unknown preset name).
        # Convert to a typed PharmaSupplyError so it gets logged with
        # the same structured context as any other validation failure.
        wrapped = ValidationError(str(error))
        logger.error(
            "command failed: %s",
            wrapped.message,
            extra={"exit_code": wrapped.exit_code},
        )
        if wrapped.hint:
            logger.warning("hint: %s", wrapped.hint)
        return wrapped.exit_code
    except LookupError as error:
        # Unknown subcommand (shouldn't happen — argparse catches this).
        logger.error("unknown command: %s", error)
        return ValidationError(str(error)).exit_code
    except PharmaSupplyError as error:
        # Expected, typed failure — exit code is carried by the exception.
        logger.error(
            "command failed: %s",
            error.message,
            extra={"exit_code": error.exit_code, "profile": error.profile},
        )
        if error.hint:
            logger.warning("hint: %s", error.hint)
        return error.exit_code
    except Exception:
        # Anything else is an internal bug — log full traceback for the
        # operator and exit with the catch-all code.
        logger.exception("unhandled exception in command %s", args.cmd)
        return 99


if __name__ == "__main__":
    raise SystemExit(main())