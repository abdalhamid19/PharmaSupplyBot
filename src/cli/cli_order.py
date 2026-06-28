"""CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import multiprocessing

from ..tawreed.order_result_merger import merge_worker_summaries
from ..tawreed.order_worker_artifact_merger import merge_order_worker_artifacts
from .item_worker_pool import report_worker_results
from .cli_order_main import (
    run_order_command,
    execute_profiles,
    run_parallel_profiles,
)
from .cli_order_single import (
    run_single_profile,
    run_single_profile_items,
    run_profile_order,
    run_profile_match_only,
)
from .cli_order_items_run import run_profile_items
from .cli_order_config import (
    apply_order_overrides,
    resolve_max_workers,
    order_bot,
)
from .cli_order_items_loading import load_order_items, load_items_from_excel, load_prevented_items, load_match_only_items_from_excel
from .cli_order_items_filtering import prepared_order_items
from .cli_order_parallel import run_parallel_order
from .cli_shared import require_state_file


# Backward compatibility aliases for tests
_load_order_items = load_order_items
_prepared_order_items = prepared_order_items
_run_parallel_order = run_parallel_order
_run_profile_order = run_profile_order
_run_profile_match_only = run_profile_match_only
_run_single_profile = run_single_profile
load_items_from_excel = load_items_from_excel
load_prevented_items = load_prevented_items
load_match_only_items_from_excel = load_match_only_items_from_excel
require_state_file = require_state_file
_order_bot = order_bot
multiprocessing = multiprocessing
merge_worker_summaries = merge_worker_summaries
merge_order_worker_artifacts = merge_order_worker_artifacts
report_worker_results = report_worker_results

__all__ = [
    "run_order_command",
    "execute_profiles",
    "run_parallel_profiles",
    "run_single_profile",
    "run_single_profile_items",
    "run_profile_items",
    "run_profile_order",
    "run_profile_match_only",
    "apply_order_overrides",
    "resolve_max_workers",
    "order_bot",
    "_load_order_items",
    "_prepared_order_items",
    "_run_parallel_order",
    "_run_profile_order",
    "_run_profile_match_only",
    "_run_single_profile",
    "load_items_from_excel",
    "load_prevented_items",
    "load_match_only_items_from_excel",
    "require_state_file",
    "_order_bot",
    "multiprocessing",
    "merge_worker_summaries",
    "merge_order_worker_artifacts",
    "report_worker_results",
]
