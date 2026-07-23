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

from contextlib import contextmanager
from rich.console import Console
from rich.table import Table


@contextmanager
def progress(label: str = "Working", *, quiet: bool = False):
    """Render a Rich progress spinner on **stderr**.

    No-op when ``quiet`` is ``True`` (cron-safe, also when stdout is
    piped). All output goes to ``stderr`` so piping stdout into ``jq``
    or another downstream tool stays clean.

    Usage::

        with progress("Placing order", quiet=is_quiet(args)):
            do_long_thing()

    The yielded object is a :class:`rich.progress.Progress` instance
    (also a no-op when ``quiet`` is True — yields ``None``).
    """
    if quiet:
        yield None
        return
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        transient=True,
        redirect_stdout=False,
    ) as prog:
        task = prog.add_task(label, total=None)
        yield prog


__all__ = ["FormatFlags", "render_table", "render_summary", "progress"]


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


def render_summary(
    command: str,
    fields: dict[str, Any],
    fmt: FormatFlags,
    *,
    success: bool = True,
) -> str:
    """Render a command summary block (the legacy ``print_command_summary``).

    Three formats:

    * **JSON** — envelope ``{"ok": bool, "data": {...} | None, "error": {...} | None}``.
      The error envelope is symmetric: success carries data, failure carries error.
    * **Plain** — ``OK command`` / ``FAIL command`` header + ``key=value`` rows.
      Stable, grep-friendly, no ANSI codes.
    * **Human** — Rich ``Panel`` with an icon (✅ / ❌) and the field rows.
    """
    if fmt.json:
        if success:
            payload = {"ok": True, "data": {"command": command, **fields}, "error": None}
        else:
            payload = {
                "ok": False,
                "data": None,
                "error": {
                    "code": "COMMAND_FAILED",
                    "message": str(fields),
                    "command": command,
                },
            }
        return json.dumps(payload, ensure_ascii=False, default=str)

    if fmt.plain:
        status = "OK" if success else "FAIL"
        header = f"{status} {command}"
        body = "\n".join(f"{k}={_stringify(v)}" for k, v in fields.items())
        return f"{header}\n{body}" if body else header

    # Human-readable Rich panel.
    from rich.panel import Panel

    icon = "✅" if success else "❌"
    body_lines = [f"{label:<14} {_stringify(value)}" for label, value in fields.items()]
    console = Console(
        no_color=fmt.no_color,
        force_terminal=False,
        record=True,
        color_system=None if fmt.no_color else "auto",
    )
    console.print(Panel("\n".join(body_lines) if body_lines else "", title=f"{icon} {command}"))
    return console.export_text()
