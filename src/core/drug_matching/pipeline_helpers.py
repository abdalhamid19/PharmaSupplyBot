"""Helper functions for MatchPipeline."""

import pandas as pd


def _manual_review_path(output_path: str) -> str:
    """Return a manual-review path next to the main output CSV."""
    path = Path(output_path)
    return str(path.with_name(f"{path.stem}_manual_review{path.suffix}"))


def _manual_review_reason_column(row: pd.Series) -> str:
    """Build a human-readable reason explaining why this row needs review."""
    parts = _manual_review_base_reasons(row)
    _append_component_review_reason(parts, row)
    return "; ".join(parts) if parts else "needs_review"


def _manual_review_base_reasons(row: pd.Series) -> list[str]:
    """Extract base reasons for manual review."""
    verified = str(row.get("verified", "") or "")
    has_match = bool(row.get("matched_product_name_en"))
    if not has_match:
        return ["no_match_found"]
    if verified == "ai_rejected":
        return ["ai_rejected_match"]
    if verified == "ai_review_rejected":
        return ["ai_review_rejected_match"]
    if verified in ("ai_confirmed", "ai_corrected", "ai_found"):
        return ["low_confidence_ai_match"]
    return _score_review_reasons(row)


def _score_review_reasons(row: pd.Series) -> list[str]:
    """Extract score-based review reasons."""
    score = pd.to_numeric(row.get("match_score", 0), errors="coerce")
    if pd.notna(score) and score < 90:
        return [f"uncertain_score({score:.0f})"]
    return []


def _append_component_review_reason(parts: list[str], row: pd.Series) -> None:
    """Append component review reason if applicable."""
    component = str(row.get("_ai_component_reason", "") or "")
    if component and component.lower() not in {"", "nan", "ok"}:
        parts.append(f"component:{component}")


__all__ = [
    "_manual_review_path",
    "_manual_review_reason_column",
    "_manual_review_base_reasons",
    "_score_review_reasons",
    "_append_component_review_reason",
]
