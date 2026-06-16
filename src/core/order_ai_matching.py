"""AI-assisted live order matching decisions."""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import dataclass, field
from typing import Callable

from .drug_matching.config import APIConfig
from .drug_matching.verifier import AIVerifier
from .matching_models import MatchDecision
from .order_ai_flow import resolve_order_ai
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

    async def _resolve_async(
        self, item: Item, decision: MatchDecision
    ) -> OrderAiOutcome:
        verifier = self._verifier_factory(
            self._settings.api_config, max_concurrent=self._settings.concurrency
        )
        try:
            return await resolve_order_ai(self._settings, verifier, item, decision)
        finally:
            await _close_verifier(verifier)

    def _no_key_outcome(self, decision: MatchDecision) -> OrderAiOutcome:
        if decision.best_match:
            return OrderAiOutcome(decision, "ai_skipped", "no_api_key", 0.0)
        return OrderAiOutcome(decision, "ai_skipped", "no_api_key", 0.0, True)


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
        return
    session = getattr(verifier, "_session", None)
    if session:
        await session.close()
