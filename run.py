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


def _force_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 before anything prints.

    On Windows the console defaults to a legacy code page (e.g.
    cp1252) which cannot encode symbols like ``✅``/``❌`` used in the
    command summaries, crashing the CLI *after* the work is done.
    ``errors="replace"`` guarantees no ``UnicodeEncodeError`` can ever
    escape a ``print()`` call, even if reconfiguration itself is
    unavailable (non-standard stream objects, odd test harnesses).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            # Stream already closed or is not a real text stream —
            # print_command_summary has its own fallback, so this is
            # safe to ignore.
            pass


def main() -> int:
    """Run the CLI command requested by the user (Typer entry point)."""
    load_dotenv()
    _force_utf8_stdio()
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
