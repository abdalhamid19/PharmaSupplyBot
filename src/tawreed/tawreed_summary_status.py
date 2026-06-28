"""Status determination logic for Tawreed order summaries."""

from ..core.candidate_identity import candidate_has_store_product_id
from ..core.matching_types import CandidateMatchDiagnostic
from ..core.order_blocked_candidate import missing_store_product_id_outcome


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
        if "cart button disabled" in lowered:
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
    hard_rejections = ("component mismatch", "identity token", "different_brand")
    return diagnostic.score >= 12.0 and not any(text in reason for text in hard_rejections)
