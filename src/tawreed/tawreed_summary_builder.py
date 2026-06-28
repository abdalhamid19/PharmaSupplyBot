"""Summary building logic for Tawreed order processing."""

import time

from ..core.matching_types import CandidateMatchDiagnostic
from .tawreed_match_logs import OrderResultSummary
from .tawreed_timing import record_timing


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
