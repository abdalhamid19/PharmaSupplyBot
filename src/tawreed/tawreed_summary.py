"""Summary building and utilities for Tawreed order processing - unified module."""

import time

from src.core.matching.candidate_identity import candidate_has_store_product_id
from src.core.matching_types import CandidateMatchDiagnostic
from src.core.ordering.order_blocked_candidate import missing_store_product_id_outcome
from src.core.utils.excel import Item
from .tawreed_dialogs import close_visible_dialogs, visible_overlay_diagnostics
from .matching.tawreed_match_logs import OrderResultSummary
from .matching.tawreed_timing import record_timing


# ============================================================================
# Summary builder (from tawreed_summary_builder.py)
# ============================================================================

class SummaryBuilder:
    """Handles building order summary objects from bot state."""

    def __init__(self, bot):
        self.bot = bot

    def build_item_summary(
        self, status: str, reason: str, elapsed: float, match_elapsed: float
    ) -> OrderResultSummary:
        """Build a compact summary object from the current bot state."""
        started_at = time.perf_counter()
        matched_name_fields = self.matched_summary_name_fields()
        record_timing(self.bot, "summary_build_seconds", time.perf_counter() - started_at)
        return OrderResultSummary(
            status=status,
            reason=reason,
            ordered_total_qty=self.bot.last_ordered_total_qty,
            **matched_name_fields,
            selected_discount_percent=self.bot.last_selected_discount_percent,
            selected_store_name=self.bot.last_selected_store_name,
            searched_queries_count=len(self.bot.last_searched_queries),
            searched_queries=" | ".join(self.bot.last_searched_queries),
            elapsed_seconds=elapsed,
            match_elapsed_seconds=match_elapsed,
            timing_seconds=dict(self.bot.last_item_timings),
        )

    def matched_summary_name_fields(self) -> dict[str, str]:
        """Return named OrderResultSummary fields for the last matched product."""
        english_name, english_source, arabic_name, matched_query = (
            self.matched_summary_fields()
        )
        return {
            "matched_product_english_name": english_name,
            "matched_product_english_name_source": english_source,
            "matched_product_arabic_name": arabic_name,
            "matched_query": matched_query,
        }

    def matched_summary_fields(self) -> tuple[str, str, str, str]:
        """Return matched product summary fields from the last recorded match decision."""
        decision = self.bot.last_match_decision
        if not decision:
            return "", "", "", ""

        candidate, query = self.extract_candidate(decision)

        if not candidate:
            return "", "", "", ""

        english_name, english_source = self.matched_english_name(candidate)
        arabic_name = str(candidate.get("productName") or "")
        return english_name, english_source, arabic_name, query

    def extract_candidate(self, decision) -> tuple[dict | None, str]:
        if decision.best_match:
            return decision.best_match.data, decision.best_match.query

        diagnostics = getattr(decision, "diagnostics", None)
        if not diagnostics:
            return None, ""

        best = max(diagnostics, key=lambda d: d.score, default=None)
        if best and getattr(best, "candidate", None):
            return best.candidate, best.query
        return None, ""

    def matched_english_name(self, candidate: dict[str, object]) -> tuple[str, str]:
        """Return matched English name and whether it came from site or fallback."""
        site_name = str(candidate.get("productNameEn") or "")
        if site_name:
            return site_name, "site"
        fallback = str(candidate.get("productNameEnFallback") or "")
        if fallback:
            return fallback, "fallback"
        return "", ""


# ============================================================================
# Dialog handler (from tawreed_summary_dialog.py)
# ============================================================================

class SummaryDialogHandler:
    """Handles dialog closing and timing for summary recording."""

    def __init__(self, bot):
        self.bot = bot

    def close_visible_dialogs_timed(self, page) -> None:
        """Close visible dialogs and accumulate the item-level wait cost."""
        started_at = time.perf_counter()
        close_visible_dialogs(page)
        record_timing(self.bot, "dialog_close_seconds", time.perf_counter() - started_at)


# ============================================================================
# Status determination (from tawreed_summary_status.py)
# ============================================================================

class SummaryStatus:
    """Handles status determination for order summaries."""

    def __init__(self, bot):
        self.bot = bot

    def skip_status(self, reason: str) -> str:
        """Return the structured summary status for one skipped item."""
        lowered = reason.lower()
        if (
            "no matching product found" in lowered
            or "no decisive match found" in lowered
            or "no decisive api match found" in lowered
        ):
            return self.unmatched_decision_status() or "no-results"
        if "manual review" in lowered:
            return "manual-review-required"
        if "unavailable" in lowered or "out of stock" in lowered:
            return "matched-but-unavailable"
        if (
            "not orderable" in lowered
            or "missing storeproductid" in lowered
            or "cart button disabled" in lowered
        ):
            return "not-orderable"
        return "skipped"

    def failure_status(self, reason: str) -> str:
        """Return the structured summary status for one failed item."""
        if "No matching product found" in reason or "No decisive match found" in reason:
            return self.unmatched_decision_status() or "no-results"
        return "failed"

    def unmatched_decision_status(self) -> str:
        """Return a more precise status for a rejected but recognized candidate."""
        if missing_store_product_id_outcome(self.bot.last_order_ai_outcome):
            return "matched-but-unavailable"
        if getattr(self.bot.last_order_ai_outcome, "manual_review", False):
            return "manual-review-required"
        decision = self.bot.last_match_decision
        if not decision or decision.best_match:
            return ""
        if any(_diagnostic_missing_orderable_identity(row) for row in decision.diagnostics):
            return "not-orderable"
        return ""


def _diagnostic_missing_orderable_identity(
    diagnostic,  # CandidateMatchDiagnostic
) -> bool:
    """Return whether a diagnostic found an otherwise acceptable non-orderable row."""
    if candidate_has_store_product_id(diagnostic.candidate):
        return False
    reason = diagnostic.rejection_reason.lower()
    if "candidate missing orderable storeproductid" in reason:
        return True
    hard_rejections = (
        "component mismatch",
        "identity token",
        "different_brand",
        "semantic token",
    )
    if any(text in reason for text in hard_rejections):
        return False
    # Soft numeric-only blocks with strong brand/form score still mean the catalog
    # row was recognized; report not-orderable instead of no-results.
    if "unrequested numeric" in reason and diagnostic.score >= 9.0:
        return True
    return diagnostic.score >= 12.0


# ============================================================================
# Utility functions (from tawreed_summary_utils.py)
# ============================================================================

def _item_error_label(item: Item) -> str:
    """Return the artifact label for one failed item."""
    return f"item_error_{item.code or 'no_code'}"


def _item_error_details(page, item: Item, error: Exception) -> str:
    """Build diagnostic artifact details for one failed item."""
    return _artifact_details(
        _item_error_label(item),
        error,
        overlay_diagnostics=visible_overlay_diagnostics(page),
        item_code=item.code,
        item_name=item.name,
        item_qty=item.qty,
    )


def _artifact_details(label: str, error: Exception, **extra: object) -> str:
    """Build plain-text diagnostic details for saved failure artifacts."""
    lines = [f"label={label}", f"error_type={type(error).__name__}", f"error={error}"]
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


__all__ = [
    # Builder
    "SummaryBuilder",
    # Dialog
    "SummaryDialogHandler",
    # Status
    "SummaryStatus",
    # Utils
    "_item_error_label",
    "_item_error_details",
    "_artifact_details",
]  # noqa: F405
