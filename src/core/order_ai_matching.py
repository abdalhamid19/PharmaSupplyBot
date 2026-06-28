"""AI-assisted live order matching decisions."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable

from .candidate_identity import candidate_store_product_id
from .drug_matching.config import APIConfig
from .drug_matching.verifier import AIVerifier
from .matching_types import MatchDecision, SearchMatch
from .utils.excel import Item


@dataclass(frozen=True)
class OrderAiSettings:
    """Runtime settings for opt-in AI matching during live order flows."""

    enabled: bool = False
    api_config: APIConfig = field(default_factory=APIConfig)
    concurrency: int = 5
    accept_confidence: float = 0.9
    verify_soft_accept_confidence: float = 0.8
    review_threshold: float = 0.95
    verify_policy: str = "score"
    search_policy: str = "review-candidates"


@dataclass(frozen=True)
class OrderAiOutcome:
    """AI decision result plus rows for trace/manual review artifacts."""

    decision: MatchDecision
    status: str
    reason: str
    confidence: float = 0.0
    manual_review: bool = False
    verify_result: dict = field(default_factory=dict)
    search_result: dict = field(default_factory=dict)
    review_result: dict = field(default_factory=dict)


class OrderAiDecisionService:
    """Resolve a live Tawreed match with optional AI verification/search/review."""

    def __init__(
        self,
        settings: OrderAiSettings,
        verifier_factory: Callable[..., AIVerifier] = AIVerifier,
    ):
        self._settings = settings
        self._verifier_factory = verifier_factory

    def resolve(self, item: Item, decision: MatchDecision) -> OrderAiOutcome:
        """Return the active decision after applying AI rules."""
        if not self._settings.enabled:
            return OrderAiOutcome(decision, "ai_disabled", "AI disabled")
        if not _has_api_key(self._settings.api_config):
            return self._no_key_outcome(decision)
        return _run_async(self._resolve_async(item, decision))

    async def _resolve_async(self, item: Item, decision: MatchDecision) -> OrderAiOutcome:
        from .order_ai_flow import resolve_order_ai
        verifier = self._verifier_factory(self._settings.api_config, max_concurrent=self._settings.concurrency)
        try:
            return await resolve_order_ai(self._settings, verifier, item, decision)
        finally:
            await _close_verifier(verifier)

    def _no_key_outcome(self, decision: MatchDecision) -> OrderAiOutcome:
        manual = not decision.best_match
        return OrderAiOutcome(decision, "ai_skipped", "no_api_key", 0.0, manual)


def _has_api_key(config: APIConfig) -> bool:
    return bool(config.api_key or config.api_keys or config.attempt_plan)


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


async def _close_verifier(verifier) -> None:
    close = getattr(verifier, "close", None)
    if close:
        await close()
    elif hasattr(verifier, "_session"):
        await verifier._session.close()


# Outcome builders
def low_confidence(decision, result, confidence, verify_result):
    """Return a manual-review outcome for low-confidence AI search."""
    return OrderAiOutcome(
        decision, "ai_low_confidence", str(result.get("reason", "")),
        confidence, True, verify_result=verify_result, search_result=result,
    )


def accepted_search(decision, match, result, confidence, verify_result):
    """Return an accepted AI-search replacement outcome."""
    active = MatchDecision(match, decision.diagnostics, "ai_search_accepted")
    return OrderAiOutcome(
        active, "ai_search_accepted", str(result.get("reason", "")), confidence,
        verify_result=verify_result, search_result=result,
    )


def rejected_search(decision, result, confidence, verify_result, reason):
    """Return a manual-review outcome for locally unsafe AI search."""
    return OrderAiOutcome(
        decision,
        "ai_rejected",
        f"AI search candidate failed local safety: {reason}",
        confidence,
        True,
        verify_result=verify_result,
        search_result=result,
    )


# Candidate conversion helpers
def candidate_name(candidate: dict[str, Any]) -> str:
    """Return the English display name used in AI prompts."""
    return str(
        candidate.get("productNameEn")
        or candidate.get("productNameEnFallback")
        or candidate.get("productName")
        or ""
    )


def candidate_ar(candidate: dict[str, Any]) -> str:
    """Return the Arabic display name used in AI prompts."""
    return str(candidate.get("productName") or "")


def candidate_price(candidate: dict[str, Any]) -> object:
    """Return candidate price when Tawreed exposes one."""
    return (
        candidate.get("retailPrice") or candidate.get("publicPrice") or
        candidate.get("price") or candidate.get("sellingPrice")
    )


def ai_candidates(decision: MatchDecision) -> list[tuple[dict, float, int]]:
    """Return verifier-compatible candidates from match diagnostics."""
    return [
        (record_from_diagnostic(diag), float(diag.score), diag.row_index)
        for diag in decision.diagnostics[:8]
    ]


def record_from_diagnostic(diag) -> dict[str, Any]:
    """Return one AI-search record from a Tawreed diagnostic."""
    candidate = diag.candidate
    return {
        "product_name_en": candidate_name(candidate),
        "product_name_ar": candidate_ar(candidate),
        "store_product_id": candidate_store_product_id(candidate),
        "price": candidate_price(candidate),
        "_raw": candidate,
        "_query": diag.query,
        "_row_index": diag.row_index,
    }


def match_from_record(record: dict[str, Any], score: float) -> SearchMatch:
    """Return a SearchMatch from an AI-selected record."""
    data = dict(record.get("_raw") or {})
    if not data:
        data = {
            "productNameEn": record.get("product_name_en", ""),
            "productName": record.get("product_name_ar", ""),
            "storeProductId": record.get("store_product_id", ""),
            "price": record.get("price", ""),
        }
    if not candidate_store_product_id(data) and record.get("store_product_id"):
        data["storeProductId"] = record.get("store_product_id")
    return SearchMatch(
        query=str(record.get("_query", "")),
        row_index=int(record.get("_row_index", 0) or 0),
        score=float(score or 0.0),
        data=data,
    )


__all__ = [
    "OrderAiSettings",
    "OrderAiOutcome",
    "OrderAiDecisionService",
    "low_confidence",
    "accepted_search",
    "rejected_search",
    "candidate_name",
    "candidate_ar",
    "candidate_price",
    "ai_candidates",
    "record_from_diagnostic",
    "match_from_record",
]
