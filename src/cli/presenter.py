"""Output layer for the Typer/Rich CLI.

Three-tier format hierarchy (auto-detected from TTY unless overridden):

* ``--format json`` — JSON envelope ``{"ok": true, "data": ...}`` on stdout.
* ``--format plain`` — TSV rows on stdout, no color, no spinner.
* default (TTY) — Rich-rendered ``Table`` on stdout, ``Progress`` on stderr.

The dispatcher is :func:`FormatFlags.resolve`; the renderer is
:func:`render_table`. Handlers return data; the CLI entry point owns
all I/O — see :mod:`src.cli.cli_shared` for the legacy summary helper
that this module replaces.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.table import Table


@dataclass(frozen=True)
class FormatFlags:
    """Resolved output format for a single command invocation."""

    json: bool = False
    plain: bool = False
    no_color: bool = False

    @classmethod
    def resolve(cls, *, explicit: str | None = None) -> "FormatFlags":
        """Pick a format from the explicit flag (or auto-detect from TTY).

        Precedence: ``--format json`` > ``--format plain`` > ``--format human``
        > auto (TTY detection on ``sys.stdout``).
        """
        if explicit == "json":
            return cls(json=True, no_color=True)
        if explicit == "plain":
            return cls(plain=True, no_color=True)
        if explicit == "human":
            return cls(no_color=False)
        # Auto-detect: piped stdout → plain (so `mycli | jq` works)
        if not sys.stdout.isatty():
            return cls(plain=True, no_color=True)
        return cls(no_color=False)


def render_table(
    rows: list[dict[str, Any]],
    columns: list[str],
    fmt: FormatFlags,
) -> str:
    """Render ``rows`` as JSON / TSV / Rich Table and return the string.

    The returned string is what the caller writes to stdout. The CLI
    entry point owns the actual ``print()`` so handlers stay pure.
    """
    if fmt.json:
        envelope = {"ok": True, "data": rows}
        return json.dumps(envelope, ensure_ascii=False, default=str)

    if fmt.plain:
        lines = ["\t".join(columns)]
        for row in rows:
            lines.append("\t".join(_stringify(row.get(col)) for col in columns))
        return "\n".join(lines)

    # Human-readable: render via Rich with no ANSI codes when no_color is set.
    table = Table(*columns, show_header=True, header_style="bold")
    for row in rows:
        table.add_row(*[_stringify(row.get(col)) for col in columns])
    console = Console(
        no_color=fmt.no_color,
        force_terminal=False,
        record=True,
        color_system=None if fmt.no_color else "auto",
    )
    console.print(table)
    return console.export_text()


def _stringify(value: Any) -> str:
    """Coerce ``value`` to a display-safe string (no trailing newline)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


__all__ = ["FormatFlags", "render_table"]
