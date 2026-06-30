"""AI-powered match verification using Agent Router API.

This module provides the main AIVerifier class interface and re-exports
helper functions from the refactored submodules.
"""

import asyncio
from typing import Any

import aiohttp

from ..config import APIConfig
from .verifier_helpers import (
    apply_conflict_penalty,
    apply_critical_conflicts,
    apply_reject_decision_override,
    component_context,
    coerce_best_index,
    extract_json,
    fallback_from_unparseable_response,
    hard_conflict_names,
    infer_is_correct,
    json_with_safe_defaults,
    loads_json_object,
    normalize_review_item,
    normalize_verify_item,
    resolve_ai_conflicts,
    route_from_norm,
)
from .verifier_request import RequestPlanner
from .verifier_response import process_api_response
from .verifier_review import ReviewVerifier
from .verifier_search import SearchVerifier
from .verifier_methods import AIVerifierMethods


class AIVerifier(AIVerifierMethods):
    """Async AI verification client with rate limiting, batching, and key/model fallback."""

    __slots__ = (
        "_cfg", "_session", "_planner", "_reviewer", "_searcher",
    )

    def __init__(self, cfg: APIConfig | None = None, max_concurrent: int = 5):
        self._cfg = cfg or APIConfig()
        self._session: aiohttp.ClientSession | None = None
        self._planner = RequestPlanner(self._cfg, asyncio.Semaphore(max_concurrent))
        self._reviewer = ReviewVerifier(self._cfg, self._planner)
        self._searcher = SearchVerifier(self._cfg, self._planner)

    def get_fallback_log(self) -> str:
        """Return and clear the API failure log for trace reporting."""
        return self._planner.get_fallback_log()

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "HTTP-Referer": "https://pharmasupplybot.local",
                "X-Title": "MediCompare Drug Matcher",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()


# Backward-compatible private aliases for existing public/test interface.
_extract_json = extract_json
_resolve_ai_conflicts = resolve_ai_conflicts


__all__ = [
    "AIVerifier",
    # Re-exported helpers for backward compatibility
    "extract_json",
    "resolve_ai_conflicts",
    "_extract_json",
    "_resolve_ai_conflicts",
    "component_context",
    "coerce_best_index",
    "normalize_verify_item",
    "normalize_review_item",
]
