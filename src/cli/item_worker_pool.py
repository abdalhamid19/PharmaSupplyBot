"""Shared helpers for item-level multiprocessing command runners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.artifact_run import current_artifact_run
from ..tawreed.tawreed_session import SessionInvalidError
from .cli_shared import invalid_session_exit


def resolve_item_workers(app_config: object, args: object) -> int:
    """Return the effective item-level worker count for one command run."""
    cli_value = getattr(args, "item_workers", None)
    if cli_value is not None:
        return int(cli_value)
    runtime = getattr(app_config, "runtime", None)
    return int(getattr(runtime, "item_workers", 1))


def build_cart_payloads(
    profile_key: str,
    chunks: list[list[Any]],
    args: object,
) -> list[dict[str, Any]]:
    """Build serializable payloads for cart-removal item workers."""
    return [
        _cart_payload(profile_key, chunk, index, args)
        for index, chunk in enumerate(chunks)
    ]


def _cart_payload(
    profile_key: str, chunk: list[Any], index: int, args: object
) -> dict[str, Any]:
    """Build one serializable cart-removal worker payload."""
    return {
        "config_path": str(Path(getattr(args, "config", "config.yaml"))),
        "profile_key": profile_key,
        "items": [(item.code, item.name) for item in chunk],
        "worker_id": index,
        "options": _cart_options(args),
    }


def _cart_options(args: object) -> dict[str, Any]:
    """Return serializable cart-removal worker options."""
    run = current_artifact_run()
    return {
        "artifact_command": run.command if run else "",
        "artifact_run_id": run.run_id if run else "",
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "stop_flag": getattr(args, "stop_flag", None),
    }


def report_worker_results(
    base_url: str,
    profile_key: str,
    results: list[dict[str, Any]],
) -> None:
    """Log worker outcomes and raise the standard invalid-session exit."""
    for result in results:
        status = result.get("status")
        if status == "session_invalid":
            error = SessionInvalidError(str(result.get("error", "")))
            raise invalid_session_exit(base_url, profile_key, error) from None
        if status == "error":
            print(f"[{profile_key}] Worker error: {result.get('error', '')}")
