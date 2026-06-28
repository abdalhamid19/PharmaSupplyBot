"""Order AI decision methods for TawreedBot."""

from __future__ import annotations

from ..core.matching_types import MatchDecision
from ..core.utils.excel import Item
from .tawreed_artifacts import append_csv_artifact
from .tawreed_order_summary import append_order_ai_trace_artifacts


class TawreedBotOrderAi:
    """Order AI decision methods for TawreedBot."""

    def resolve_order_ai_decision(
        self, item: Item, decision: MatchDecision
    ) -> MatchDecision:
        """Apply opt-in AI verification/search and persist trace rows."""
        if not self.order_ai_service:
            return decision
        outcome = self.order_ai_service.resolve(item, decision)
        self.last_order_ai_outcome = outcome
        self._record_order_ai_rows(item, outcome)
        self.last_match_decision = outcome.decision
        return outcome.decision

    def _record_order_ai_rows(self, item: Item, outcome) -> None:
        """Append live-order AI trace and manual-review rows."""
        row = self._order_ai_trace_row(item, outcome)
        append_csv_artifact(self.profile_key, "matching_trace", [row])
        append_order_ai_trace_artifacts(
            self.profile_key, item, outcome, self.summary_label_suffix
        )

    def _order_ai_trace_row(self, item: Item, outcome) -> dict[str, object]:
        """Return one trace-compatible row for the AI order decision."""
        match = outcome.decision.best_match
        return {
            "phase": "order_ai",
            "item_code": item.code,
            "item_name": item.name,
            "item_qty": item.qty,
            "final_status": outcome.status,
            "final_reason": outcome.reason,
            **self._order_ai_candidate_fields(match, outcome),
            "selection_reason": outcome.reason,
        }

    def _order_ai_candidate_fields(self, match, outcome) -> dict[str, object]:
        """Return candidate columns for one AI trace row."""
        candidate = match.data if match else {}
        return {
            "candidate_rank": "",
            "candidate_name_en": candidate.get("productNameEn", ""),
            "candidate_name_ar": candidate.get("productName", ""),
            "candidate_id": candidate.get("storeProductId", ""),
            "candidate_score": round(outcome.confidence, 6),
            "accepted": bool(match and not outcome.manual_review),
            "accepted_reason": outcome.status,
            "rejection_reason": outcome.reason if outcome.manual_review else "",
            "query": match.query if match else "",
            "row_index": match.row_index if match else "",
        }
