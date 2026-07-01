"""Order command building helpers for Streamlit."""

from __future__ import annotations

from pathlib import Path


# ============================================================================
# Command building
# ============================================================================


def order_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> list[str]:
    """Return the CLI command arguments for one order run."""
    command = _order_base_command(config_path, excel_path, form_values)
    command.extend(_order_profile_args(form_values))
    command.extend(_order_debug_args(form_values))
    command.extend(_order_execution_args(form_values))
    command.extend(_order_worker_args(form_values))
    command.extend(_order_discount_args(form_values))
    command.extend(_order_item_range_args(form_values))
    command.extend(_matching_risk_command_args(form_values))
    command.extend(_order_ai_command_args(form_values))
    return command


def _order_base_command(
    config_path: Path, excel_path: Path, form_values: dict[str, object]
) -> list[str]:
    """Return the base order command with config and excel."""
    command = ["order", "--config", str(config_path), "--excel", str(excel_path)]
    command.extend(["--limit", str(form_values["limit"])])
    return command


def _order_profile_args(form_values: dict[str, object]) -> list[str]:
    """Return profile-related CLI arguments."""
    if form_values["profile_mode"] == "Single profile":
        return ["--profile", str(form_values["profile_key"])]
    return ["--all-profiles"]


def _order_debug_args(form_values: dict[str, object]) -> list[str]:
    """Return debug and mode CLI arguments."""
    args = []
    if form_values["debug_browser"]:
        args.append("--debug-browser")
    if form_values.get("resume"):
        args.append("--resume")
    if form_values.get("match_only"):
        args.append("--match-only")
    return args


def _order_execution_args(form_values: dict[str, object]) -> list[str]:
    """Return execution mode CLI arguments."""
    return ["--execution-mode", _order_execution_mode(form_values)]


def _order_worker_args(form_values: dict[str, object]) -> list[str]:
    """Return item workers CLI arguments."""
    from .streamlit_order_form import _int_form_value
    item_workers = _int_form_value(form_values, "item_workers", 1)
    return ["--item-workers", str(item_workers)]


def _order_discount_args(form_values: dict[str, object]) -> list[str]:
    """Return discount-related CLI arguments."""
    from .streamlit_order_form import _float_form_value
    args = []
    if form_values.get("highest_discount"):
        args.extend(["--warehouse-mode", "max_discount"])
    min_discount = _float_form_value(form_values, "min_discount_percent", 0.0)
    if min_discount > 0:
        args.extend(["--min-discount-percent", f"{min_discount:g}"])
    prevented = str(form_values.get("prevented_items_excel") or "")
    if prevented:
        args.extend(["--prevented-items-excel", prevented])
    return args


def _order_item_range_args(form_values: dict[str, object]) -> list[str]:
    """Return item range (start/end) CLI arguments."""
    from .streamlit_order_form import _int_form_value
    args = []
    start_item = _int_form_value(form_values, "start_item", 1)
    if start_item > 1:
        args.extend(["--start-item", str(start_item)])
    end_item = _int_form_value(form_values, "end_item", 0)
    if end_item > 0:
        args.extend(["--end-item", str(end_item)])
    return args


def _matching_risk_command_args(form_values: dict[str, object]) -> list[str]:
    """Return CLI arguments for safe or aggressive matching policy."""
    return [
        "--matching-risk-policy",
        str(form_values.get("matching_risk_policy") or "safe"),
        "--flagged-match-action",
        str(form_values.get("flagged_match_action") or "manual-review-only"),
    ]


def _order_execution_mode(form_values: dict[str, object]) -> str:
    """Return the fastest safe execution mode for the requested order run."""
    mode = str(form_values.get("execution_mode", "auto") or "auto")
    if form_values.get("match_only") and mode == "auto":
        return "api"
    return mode


def _order_ai_command_args(form_values: dict[str, object]) -> list[str]:
    """Return CLI arguments for optional live-order AI matching."""
    from .streamlit_order_form import _append_optional_ai_text, _int_form_value, _float_form_value
    if not form_values.get("enable_order_ai"):
        return []
    args = ["--ai", *_order_ai_provider_args(form_values)]
    args.extend(_order_ai_threshold_args(form_values))
    _append_optional_ai_text(args, "--model", form_values.get("ai_model"))
    _append_optional_ai_text(args, "--review-model", form_values.get("ai_review_model"))
    return args


def _order_ai_provider_args(form_values: dict[str, object]) -> list[str]:
    """Return provider and policy CLI args for order AI."""
    from .streamlit_order_form import _int_form_value
    return [
        "--provider",
        str(form_values.get("ai_provider") or "openrouter"),
        "--concurrency",
        str(_int_form_value(form_values, "ai_concurrency", 5)),
        "--ai-verify-policy",
        str(form_values.get("ai_verify_policy") or "score"),
        "--ai-search-policy",
        str(form_values.get("ai_search_policy") or "review-candidates"),
    ]


def _order_ai_threshold_args(form_values: dict[str, object]) -> list[str]:
    """Return confidence threshold CLI args for order AI."""
    from .streamlit_order_form import _float_form_value
    accept = _float_form_value(form_values, "ai_accept_confidence", 0.9)
    review = _float_form_value(form_values, "ai_review_threshold", 0.95)
    return ["--ai-accept-confidence", f"{accept:g}", "--ai-review-threshold", f"{review:g}"]


__all__ = [
    "order_command",
    "_order_base_command",
    "_order_profile_args",
    "_order_debug_args",
    "_order_execution_args",
    "_order_worker_args",
    "_order_discount_args",
    "_order_item_range_args",
    "_matching_risk_command_args",
    "_order_execution_mode",
    "_order_ai_command_args",
    "_order_ai_provider_args",
    "_order_ai_threshold_args",
]
