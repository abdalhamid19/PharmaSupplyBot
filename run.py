"""CLI entry point for Tawreed authentication, ordering, and exports.

This module is intentionally tiny now: it loads ``.env`` and delegates
to the Typer application in :mod:`src.cli.typer_app`. Exit-code
mapping for ``PharmaSupplyError`` happens inside ``_run_registered``.

The legacy argparse flow (parser construction, ``--show-completion``,
preset/defaults injection, the catch-all ``99`` exit code) is gone —
all of those concerns are now owned by Typer + the registry.
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

# Importing cli_commands populates the command registry via decorators.
from src.cli import cli_commands  # noqa: F401
from src.cli.typer_app import app


def main() -> int:
    """Run the CLI command requested by the user (Typer entry point)."""
    load_dotenv()
    try:
        # Typer's ``app()`` raises ``SystemExit`` on completion; we
        # normalise the exit code so ``raise SystemExit(main())`` in
        # ``__main__`` works as expected.
        app()
        return 0
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0


if __name__ == "__main__":
    sys.exit(main())
