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
    args = build_parser().parse_args()

    # ✨ Initialize logging BEFORE running the command so every module
    # that grabs a logger at import time sees the configured handlers.
    configure_logging(_resolve_logging_config(args))
    logger = logging.getLogger(__name__)

    try:
        config_path = Path(args.config)
        app_config = load_config(config_path)
        command = get_command(args.cmd)
        logger.debug(
            "dispatching command",
            extra={"cmd": args.cmd, "config": str(config_path)},
        )
        return command(app_config, args)
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
            logger.info("hint: %s", error.hint)
        return error.exit_code
    except Exception:
        # Anything else is an internal bug — log full traceback for the
        # operator and exit with the catch-all code.
        logger.exception("unhandled exception in command %s", args.cmd)
        return 99


if __name__ == "__main__":
    raise SystemExit(main())