"""Bridge between Typer's parsed context and the existing command registry.

Each registered handler takes ``(app_config, args: argparse.Namespace) -> int``.
This module materialises a flat ``Namespace`` from the Typer-bound parameters
so handlers don't need to change.
"""

from __future__ import annotations

from argparse import Namespace
from typing import Any

from typer import Context


def ns_from_ctx(ctx: Context, *, cmd: str) -> Namespace:
    """Return an ``argparse.Namespace`` mirroring ``ctx.params`` + top-level options.

    Top-level options set on the parent ``@app.callback`` (``--quiet``,
    ``--log-level``, ``--json-log-records``, ``--rich-logs``) are
    promoted onto the namespace so handlers can keep using
    ``args.quiet``, ``args.log_level``, etc.

    The returned namespace has ``cmd`` attribute set to the subcommand
    name (matches the legacy ``argparse.Namespace`` shape used by the
    registered command callables).
    """
    obj = getattr(ctx, "obj", None) or {}
    params: dict[str, Any] = dict(ctx.params or {})
    payload: dict[str, Any] = {
        **params,
        "cmd": cmd,
        "quiet": bool(obj.get("quiet", False)),
        "log_level": obj.get("log_level", "INFO"),
        "json_logs": bool(obj.get("json_logs", False)),
        "rich_logs": bool(obj.get("rich_logs", False)),
    }
    return Namespace(**payload)


__all__ = ["ns_from_ctx"]
