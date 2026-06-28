"""Order item loading and filtering logic."""

from __future__ import annotations

from pathlib import Path

from ..core.utils.excel import Item
from .cli_order_items_loading import (
    load_order_items,
    load_regular_order_items,
    manual_review_correction_items,
    require_order_excel,
    load_items_for_order_mode,
    prevented_items_path,
    reject_prevented_excel_as_order_source,
)
from .cli_order_items_filtering import (
    slice_items,
    excel_load_limit,
    prepared_order_items,
    limited_order_items,
    order_item_limit,
    match_only,
    ensure_non_empty_items,
)
from .cli_order_items_summary import (
    summary_label,
    processed_summary_item_keys,
    latest_summary_path,
    item_key,
)


def order_bot_options(args) -> dict[str, object]:
    """Extract bot options from CLI arguments."""
    from .cli_order_ai import order_ai_settings
    stop_flag = getattr(args, "stop_flag", None)
    return {
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "stop_flag_path": Path(stop_flag) if stop_flag else None,
        "fast_search": bool(getattr(args, "fast_search", False)),
        "match_only": match_only(args),
        "order_ai_settings": order_ai_settings(args),
        "execution_mode": str(getattr(args, "execution_mode", "auto")),
        "matching_risk_policy": str(getattr(args, "matching_risk_policy", "safe")),
        "flagged_match_action": str(
            getattr(args, "flagged_match_action", "manual-review-only")
        ),
    }


__all__ = [
    "load_order_items",
    "load_regular_order_items",
    "manual_review_correction_items",
    "require_order_excel",
    "load_items_for_order_mode",
    "slice_items",
    "excel_load_limit",
    "prevented_items_path",
    "reject_prevented_excel_as_order_source",
    "prepared_order_items",
    "limited_order_items",
    "order_item_limit",
    "match_only",
    "summary_label",
    "processed_summary_item_keys",
    "latest_summary_path",
    "item_key",
    "order_bot_options",
    "ensure_non_empty_items",
]
