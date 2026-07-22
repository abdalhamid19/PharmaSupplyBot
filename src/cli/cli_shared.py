"""Shared helpers and common logic for CLI command runners."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Mapping

from src.core.config.config_models import AppConfig, ProfileConfig
from src.core.errors import APIUnavailableError, AuthError
from src.tawreed.tawreed import TawreedBot
from src.tawreed.auth.tawreed_session import SessionInvalidError


# ─────────────────────────── Command summary helper ──────────────────
#
# Each CLI subcommand handler returns just an ``int`` (the exit code).
# Before returning, it calls :func:`print_command_summary` with a
# dict of structured fields. We render them as a small, consistent
# block so operators (and CI parsers) get the same shape from every
# command:
#
#     ✅ order completed
#        - processed: 18/20 items
#        - matched:   16 (89%)
#        - flagged:   2 (manual review)
#        - duration:  2m 14s
#        - summary:   artifacts/wardany/order_summary_21072026.csv
#
# Behaviour:
#   * Sent to **stdout** by default (the operator's terminal).
#   * Hidden entirely under ``--quiet`` (so cron logs stay clean).
#   * In ``--json-logs`` mode, still printed as text (this is a
#     *command* summary, distinct from log records).
#   * ``success=False`` swaps the ✅ for ❌ and emits to **stderr**
#     so the operator cannot miss it in a piped command.
#
# The function is **pure I/O** — it never raises. Failures to format
# a field fall back to ``str(value)`` so a typo in the caller can't
# crash the CLI.


_STATUS_ICONS = {
    True: "✅",
    False: "❌",
}


def print_command_summary(
    command: str,
    fields: Mapping[str, object] | None = None,
    *,
    success: bool = True,
    quiet: bool = False,
) -> None:
    """Print a structured summary block for ``command``.

    Args:
        command: Subcommand name (e.g. ``"order"``, ``"auth"``).
        fields:  Ordered-ish mapping of label → value. Common keys:
                 processed, matched, flagged, failed, duration,
                 summary (path to artifact), profile, ...
        success: If ``False``, the header becomes ``❌`` and the
                 block is sent to stderr so the operator sees it.
        quiet:   If ``True``, emit nothing (cron-friendly).
    """
    if quiet:
        return

    icon = _STATUS_ICONS[success]
    status_word = "completed" if success else "failed"
    line = f"{icon} {command} {status_word}"
    stream = sys.stdout if success else sys.stderr

    print(line, file=stream)
    if not fields:
        return
    # Compute a fixed column width so the values line up under the
    # header. We don't pad to the longest key — that looks ragged
    # when one key is much longer than the others. Instead we use a
    # soft cap of 12 chars which covers all current field names.
    for label, value in fields.items():
        # Repr the value in a shell-friendly way (no newlines, no
        # giant lists dumped to terminal). For Path objects we use
        # ``str`` so it shows as a clean POSIX path.
        rendered = _render_field(value)
        print(f"   - {label:<12} {rendered}", file=stream)


def _render_field(value: object) -> str:
    """Format one summary field for terminal output."""
    if value is None:
        return "-"
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        # Trim trailing zeros from durations / percentages so the
        # block stays one line per row.
        return f"{value:g}"
    if isinstance(value, (list, tuple)):
        # Compact list: "[a, b, c]" rather than dumping 30 items.
        if len(value) <= 3:
            return "[" + ", ".join(str(v) for v in value) + "]"
        return f"[{len(value)} items]"
    return str(value)


def format_duration(seconds: float | int | None) -> str:
    """Render a duration in seconds as a short human string.

    ``None`` returns ``"-"`` so callers can pass an unset timer.
    """
    if seconds is None:
        return "-"
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m"


# ─────────────────────────── Timer context manager ──────────────────
#
# Convenience for handlers that want to time their own work. The
# ``summary_fields`` dict is updated IN PLACE with a ``"duration"``
# entry, then passed to :func:`print_command_summary`.


class CommandTimer:
    """Context manager that records wall-clock duration.

    Usage::

        timer = CommandTimer()
        with timer:
            do_the_thing()
        print_command_summary("order", {"duration": timer.seconds})
    """

    def __init__(self) -> None:
        self.seconds: float = 0.0
        self._start: float | None = None

    def __enter__(self) -> "CommandTimer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *exc: object) -> None:
        if self._start is not None:
            self.seconds = time.monotonic() - self._start


# ─────────────────────────── Quiescence check ──────────────────────


def is_quiet(args: argparse.Namespace | object) -> bool:
    """Return True if the user passed ``--quiet``.

    Tolerates a plain object (test double) that lacks the attribute.
    """
    return bool(getattr(args, "quiet", False))


# ─────────────────────────── Existing helpers (unchanged) ───────────


def build_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    debug_browser: bool = False,
    **options,
) -> TawreedBot:
    """Create a Tawreed bot instance for one profile."""
    return TawreedBot(
        app_config,
        profile_key,
        profile,
        state_path(profile_key),
        debug_browser=debug_browser,
        **options,
    )


def require_state_file(profile_key: str) -> None:
    """Ensure the profile has a saved Playwright storage state file.

    Raises :class:`AuthError` (exit code 3) when the state is missing so
    the runner can map it to a clean CLI failure instead of a stack trace.
    """
    saved_state_path = state_path(profile_key)
    if saved_state_path.exists():
        return
    raise AuthError(
        f"Missing saved session state for profile '{profile_key}'.",
        profile=profile_key,
        hint=f"Run: py run.py auth --profile {profile_key}",
    )


def state_path(profile_key: str) -> Path:
    """Return the storage-state path for one profile."""
    state_dir = Path("state")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{profile_key}.json"


def raise_invalid_session(
    profile_key: str, error: SessionInvalidError
) -> None:
    """Raise the standard session-expired error after opening browser reauth.

    Replaces the legacy ``invalid_session_exit`` helper. The previous
    implementation returned a ``SystemExit`` instance (which only works
    when the caller is itself about to ``raise`` it). Raising directly
    is safer, more consistent, and gives us a typed ``AuthError`` to
    log with ``logger.exception``.
    """
    raise AuthError(
        f"Session for profile '{profile_key}' is not valid: {error}",
        profile=profile_key,
        hint=f"Run: py run.py auth --profile {profile_key}",
    )


def raise_api_unavailable(profile_key: str, error: Exception) -> None:
    """Raise the standard API-unavailable error for strict execution modes.

    Replaces the legacy ``api_unavailable_exit`` helper. The CLI runner
    converts :class:`APIUnavailableError` into exit code 4.
    """
    raise APIUnavailableError(
        f"Tawreed API unavailable for profile '{profile_key}': {error}. "
        "Use --execution-mode auto or browser, or refresh auth with: "
        f"py run.py auth --profile {profile_key}",
        profile=profile_key,
    )


__all__ = [
    "build_bot",
    "require_state_file",
    "state_path",
    "raise_invalid_session",
    "raise_api_unavailable",
]