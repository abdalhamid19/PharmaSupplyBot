"""Command building for Streamlit order tab."""

from __future__ import annotations

from pathlib import Path

from .streamlit_order_helpers import (
    _int_form_value,
    _float_form_value,
    _append_optional_ai_text,
)


def order_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> list[str]:
    """Return the CLI command arguments for one order run."""
    command = ["order", "--config", str(config_path), "--excel", str(excel_path)]
    command.extend(["--limit", str(form_values["limit"])])
    if form_values["profile_mode"] == "Single profile":
        command.extend(["--profile", str(form_values["profile_key"])])
    else:
        command.append("--all-profiles")
    if form_values["debug_browser"]:
        command.append("--debug-browser")
    if form_values.get("resume"):
        command.append("--resume")
    if form_values.get("match_only"):
        command.append("--match-only")
    command.extend(["--execution-mode", _order_execution_mode(form_values)])
    item_workers = _int_form_value(form_values, "item_workers", 1)
    command.extend(["--item-workers", str(item_workers)])
    if form_values.get("highest_discount"):
        command.extend(["--warehouse-mode", "max_discount"])
    min_discount_percent = _float_form_value(form_values, "min_discount_percent", 0.0)
    if min_discount_percent > 0:
        command.extend(["--min-discount-percent", f"{min_discount_percent:g}"])
    prevented_items_excel = str(form_values.get("prevented_items_excel") or "")
    if prevented_items_excel:
        command.extend(["--prevented-items-excel", prevented_items_excel])
        
    start_item = _int_form_value(form_values, "start_item", 1)
    if start_item > 1:
        command.extend(["--start-item", str(start_item)])
        
    end_item = _int_form_value(form_values, "end_item", 0)
    if end_item > 0:
        command.extend(["--end-item", str(end_item)])
        
    command.extend(_matching_risk_command_args(form_values))
    command.extend(_order_ai_command_args(form_values))
    return command


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
    if not form_values.get("enable_order_ai"):
        return []
    args = ["--ai", *_order_ai_provider_args(form_values)]
    args.extend(_order_ai_threshold_args(form_values))
    _append_optional_ai_text(args, "--model", form_values.get("ai_model"))
    _append_optional_ai_text(args, "--review-model", form_values.get("ai_review_model"))
    return args


def _order_ai_provider_args(form_values: dict[str, object]) -> list[str]:
    """Return provider and policy CLI args for order AI."""
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
    accept = _float_form_value(form_values, "ai_accept_confidence", 0.9)
    review = _float_form_value(form_values, "ai_review_threshold", 0.95)
    return ["--ai-accept-confidence", f"{accept:g}", "--ai-review-threshold", f"{review:g}"]
