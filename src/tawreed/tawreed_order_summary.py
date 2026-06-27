"""Order summary and recording logic for Tawreed order processing."""

from __future__ import annotations

import time

from ..core.candidate_identity import candidate_has_store_product_id
from ..core.matching_models import CandidateMatchDiagnostic
from ..core.order_blocked_candidate import missing_store_product_id_outcome
from ..core.utils.excel import Item
from .tawreed_artifacts import dump_artifacts
from .tawreed_dialogs import close_visible_dialogs, visible_overlay_diagnostics
from .tawreed_match_logs import OrderResultSummary, append_order_result_summary
from .tawreed_match_only_summary import append_match_only_summary
from .tawreed_order_run_artifacts import append_order_item_artifacts
from .tawreed_timing import record_timing


class OrderSummaryRecorder:
    """Handles recording of order summaries and match-only summaries."""

    def __init__(self, bot):
        """Initialize summary recorder with bot instance."""
        self.bot = bot

    def record_success(self, item: Item, started_at: float) -> None:
        """Record a successful add-to-cart summary."""
        self.record_item_summary(
            item,
            status="added-to-cart",
            reason="Added to cart.",
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.bot.last_match_elapsed_seconds,
        )

    def record_match_only_success(self, item: Item, started_at: float) -> None:
        """Record a successful product match that did not touch the cart."""
        self.record_match_only_summary(
            item,
            status="matched-only",
            reason="Matched product only; item was not added to cart.",
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.bot.last_match_elapsed_seconds,
        )

    def record_match_only_skip(
        self, item: Item, error: Exception, started_at: float
    ) -> None:
        """Record a skipped item during match-only mode."""
        reason = str(error)
        self.record_match_only_summary(
            item,
            self.skip_status(reason),
            reason,
            time.perf_counter() - started_at,
            self.bot.last_match_elapsed_seconds,
        )
        print(
            _console_safe(
                f"[{self.bot.profile_key}] Skipped item {item.code} / {item.name}: {error}"
            )
        )

    def record_match_only_failure(
        self, page, item: Item, error: Exception, started_at: float
    ) -> None:
        """Record a failed match-only item and capture diagnostics."""
        reason = str(error)
        self.close_visible_dialogs_timed(page)
        self.record_match_only_summary(
            item,
            self.failure_status(reason),
            reason,
            time.perf_counter() - started_at,
            self.bot.last_match_elapsed_seconds,
        )
        self.print_failed_item(item, error)
        dump_artifacts(
            page,
            self.bot.profile_key,
            _item_error_label(item),
            _item_error_details(page, item, error),
        )

    def record_skip(self, item: Item, error: Exception, started_at: float) -> None:
        """Record a skipped item summary."""
        reason = str(error)
        self.record_item_summary(
            item,
            status=self.skip_status(reason),
            reason=reason,
            elapsed_seconds=time.perf_counter() - started_at,
            match_elapsed_seconds=self.bot.last_match_elapsed_seconds,
        )
        print(
            _console_safe(
                f"[{self.bot.profile_key}] Skipped item {item.code} / {item.name}: {error}"
            )
        )

    def record_failure(
        self, page, item: Item, error: Exception, started_at: float
    ) -> None:
        """Record a technical failure and capture diagnostic artifacts."""
        reason = str(error)
        self.close_visible_dialogs_timed(page)
        self.record_failure_summary(item, reason, started_at)
        self.print_failed_item(item, error)
        dump_artifacts(
            page,
            self.bot.profile_key,
            label=_item_error_label(item),
            details=_item_error_details(page, item, error),
        )

    def close_visible_dialogs_timed(self, page) -> None:
        """Close visible dialogs and accumulate the item-level wait cost."""
        started_at = time.perf_counter()
        close_visible_dialogs(page)
        record_timing(self.bot, "dialog_close_seconds", time.perf_counter() - started_at)

    def record_failure_summary(self, item: Item, reason: str, started_at: float) -> None:
        """Append the summary row for one failed item."""
        self.record_item_summary(
            item,
            self.failure_status(reason),
            reason,
            time.perf_counter() - started_at,
            self.bot.last_match_elapsed_seconds,
        )

    def print_failed_item(self, item: Item, error: Exception) -> None:
        """Print one console-safe failed item message."""
        message = f"[{self.bot.profile_key}] Failed item {item.code} / {item.name}: {error}"
        print(_console_safe(message))

    def record_item_summary(
        self,
        item: Item,
        status: str,
        reason: str,
        elapsed_seconds: float,
        match_elapsed_seconds: float,
    ) -> None:
        """Append one execution-summary row for the processed item."""
        summary = self.build_item_summary(
            status, reason, elapsed_seconds, match_elapsed_seconds
        )
        append_order_result_summary(
            self.bot.profile_key, item, summary, label_suffix=self.bot.summary_label_suffix
        )
        self.record_order_run_artifacts(item, summary)

    def record_match_only_summary(
        self,
        item: Item,
        status: str,
        reason: str,
        elapsed_seconds: float,
        match_elapsed_seconds: float,
    ) -> None:
        """Append one detailed match-only summary for the processed item."""
        summary = self.build_item_summary(
            status, reason, elapsed_seconds, match_elapsed_seconds
        )
        append_match_only_summary(
            self.bot.profile_key,
            item,
            summary,
            self.bot.last_match_decision,
            label_suffix=self.bot.summary_label_suffix,
        )
        self.record_order_run_artifacts(item, summary)

    def record_order_run_artifacts(self, item: Item, summary: OrderResultSummary) -> None:
        """Append per-item summary and manual-review artifacts for this run."""
        append_order_item_artifacts(
            self.bot.profile_key,
            item,
            summary,
            self.bot.last_match_decision,
            self.bot.last_order_ai_outcome,
            self.bot.summary_label_suffix,
            self.bot.config.matching,
        )

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


def _item_error_label(item: Item) -> str:
    """Return the artifact label for one failed item."""
    return f"item_error_{item.code or 'no_code'}"


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


def _console_safe(text: str) -> str:
    """Return text that can be printed on cp1252 Windows consoles without crashing."""
    return text.encode("cp1252", errors="replace").decode("cp1252")
