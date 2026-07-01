"""Summary formatting functions for Tawreed order processing."""

from __future__ import annotations

from src.core.ordering.order_run_artifact_rows import text_block
from ..artifacts.tawreed_artifacts import append_csv_artifact, append_text_artifact


def _final_trace_row(row: dict[str, object]) -> dict[str, object]:
    """Build the final trace row from item summary row."""
    return {
        "phase": "item_final",
        "item_code": row["item_code"],
        "item_name": row["item_name"],
        "ai_status": row["ai_status"],
        "result": row["status"],
        "confidence": row["ai_confidence"],
        "model_used": row["ai_model"],
        "provider_used": row["ai_provider"],
        "reason": row["reason"],
        "manual_review_required": row["manual_review_required"],
        "manual_review_category": row.get("manual_review_category", ""),
        "manual_review_reason_detail": row.get("manual_review_reason_detail", ""),
        "manual_review_blocking_phase": row.get("manual_review_blocking_phase", ""),
        "candidate_safety_reason": row.get("candidate_safety_reason", ""),
    }


def _append_item_summary_row(
    profile_key: str, row: dict[str, object], label_suffix: str | None
) -> None:
    """Append one item summary row to CSV and TXT artifacts."""
    append_csv_artifact(profile_key, "order_item_summary", [row], label_suffix)
    append_text_artifact(
        profile_key, "order_item_summary", text_block("item", row), label_suffix
    )


def _append_final_trace_row(
    profile_key: str, row: dict[str, object], label_suffix: str | None
) -> None:
    """Append the final trace row to CSV and TXT artifacts."""
    final_row = _final_trace_row(row)
    append_csv_artifact(profile_key, "order_ai_trace", [final_row], label_suffix)
    append_text_artifact(
        profile_key, "order_ai_trace", text_block("item_final", final_row), label_suffix
    )


def _text_rows(title: str, rows: list[dict[str, object]]) -> str:
    """Convert a list of rows to text block format."""
    return "".join(text_block(title, row) for row in rows)


__all__ = [
    "_final_trace_row",
    "_append_item_summary_row",
    "_append_final_trace_row",
    "_text_rows",
]
