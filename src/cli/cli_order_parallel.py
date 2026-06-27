"""Parallel order execution logic."""

import multiprocessing
from typing import Any

from ..core.utils.chunking import split_into_chunks
from ..core.artifact_run import current_artifact_run
from ..tawreed.order_result_merger import merge_worker_summaries
from ..tawreed.order_worker_artifact_merger import merge_order_worker_artifacts
from .cli_order_items import summary_label
from .item_worker_pool import report_worker_results


def run_parallel_order(
    app_config,
    profile_key: str,
    items,
    args,
    item_workers: int,
) -> None:
    """Split items across multiprocessing workers and merge results."""
    from multiprocessing import Manager
    from .item_worker_runner import run_order_chunk

    materialized = list(items)
    chunks = split_into_chunks(materialized, item_workers)
    manager = Manager()
    auth_lock = manager.Lock()
    
    payloads = build_order_payloads(profile_key, chunks, args, auth_lock)
    results = execute_order_workers(profile_key, chunks, payloads)
    merge_order_worker_outputs(profile_key, args)
    report_worker_results(app_config.base_url, profile_key, results)


def execute_order_workers(profile_key, chunks, payloads):
    """Execute order workers in parallel."""
    from .item_worker_runner import run_order_chunk
    print(f"[{profile_key}] Launching {len(chunks)} parallel item workers...")
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=len(chunks)) as pool:
        return pool.map(run_order_chunk, payloads)


def merge_order_worker_outputs(profile_key: str, args) -> None:
    """Merge all order worker output partitions for the active run."""
    merge_worker_summaries(profile_key, summary_label(args))
    merge_order_worker_artifacts(
        profile_key, ("order_item_summary", "order_ai_trace", "manual_review")
    )


def build_order_payloads(
    profile_key: str,
    chunks: list[list[Any]],
    args,
    auth_lock,
) -> list[dict[str, Any]]:
    """Build serializable payloads for each order worker."""
    from pathlib import Path
    from .cli_order_ai import order_ai_settings
    config_path = str(Path(getattr(args, "config", "config.yaml")))
    options = worker_options(args, auth_lock)
    return [
        {
            "config_path": config_path,
            "profile_key": profile_key,
            "items": [(it.code, it.name, it.qty) for it in chunk],
            "worker_id": idx,
            "options": options,
        }
        for idx, chunk in enumerate(chunks)
    ]


def worker_options(args, auth_lock=None) -> dict[str, Any]:
    """Extract serializable worker options from the CLI namespace."""
    from .cli_order_ai import order_ai_settings
    from .cli_order_items import match_only
    run = current_artifact_run()
    return {
        "artifact_command": run.command if run else "",
        "artifact_run_id": run.run_id if run else "",
        "order_ai_settings": order_ai_settings(args),
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "fast_search": bool(getattr(args, "fast_search", False)),
        "match_only": match_only(args),
        "execution_mode": str(getattr(args, "execution_mode", "auto")),
        "matching_risk_policy": str(getattr(args, "matching_risk_policy", "safe")),
        "flagged_match_action": str(
            getattr(args, "flagged_match_action", "manual-review-only")
        ),
        "stop_flag": getattr(args, "stop_flag", None),
        "warehouse_mode": getattr(args, "warehouse_mode", None),
        "min_discount_percent": getattr(args, "min_discount_percent", None),
        "auth_lock": auth_lock,
    }


__all__ = [
    "run_parallel_order",
    "execute_order_workers",
    "merge_order_worker_outputs",
    "build_order_payloads",
    "worker_options",
]
