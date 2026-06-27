"""AI-powered match verification using Agent Router API.

This module provides the main AIVerifier class interface and re-exports
helper functions from the refactored submodules.
"""

import asyncio
from typing import Any

import aiohttp

from .config import APIConfig
from .pricing import price_context
from .prompts import SYSTEM_PROMPT, VERIFY_PROMPT, render_prompt
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

__all__ = [
    "AIVerifier",
    # Re-exported helpers for backward compatibility
    "extract_json",
    "resolve_ai_conflicts",
    "component_context",
    "coerce_best_index",
    "normalize_verify_item",
    "normalize_review_item",
]


class AIVerifier:
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

    async def verify_one(
        self, drug_a: str, drug_b: str, drug_b_ar: str = "",
        algo_score="", algo_method="", inventory_price=None,
        candidate_price=None,
    ) -> dict[str, Any]:
        """Verify a single match. Returns {is_correct, reason, confidence}."""
        if not self._cfg.api_key:
            return {"is_correct": True, "reason": "no_api_key", "confidence": 0.5}

        ar_line = f"\nDRUG B Arabic: {drug_b_ar}" if drug_b_ar else ""
        algorithm_context = (
            f"score={algo_score or '-'}, method={algo_method or '-'}"
        )
        prompt = render_prompt(
            VERIFY_PROMPT,
            drug_a=drug_a,
            drug_b=drug_b,
            drug_b_ar_line=ar_line,
            drug_a_context=component_context(drug_a),
            drug_b_context=component_context(drug_b),
            algorithm_context=algorithm_context,
            price_context=price_context(inventory_price, candidate_price),
        )
        payload = {
            "model": self._cfg.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._cfg.max_tokens,
            "temperature": self._cfg.temperature,
            "response_format": {"type": "json_object"},
        }

        result = await self._planner.call_api(self._session, payload)
        if result is None:
            return {"is_correct": True, "reason": "all_api_failed", "confidence": 0.0, "api_failed": True}
        # Remove 'agree' key if present (not used in verify)
        result.pop("agree", None)
        return process_api_response(result)

    async def verify_batch(self, matches: list[tuple]) -> list[dict[str, Any]]:
        """Verify a batch of matches. Each item is (drug_a, drug_b, drug_b_ar, row_index)."""
        normalized = [normalize_verify_item(item) for item in matches]
        tasks = [
            self.verify_one(a, b, ar, score, method, inv_price, cand_price)
            for (
                a, b, ar, _, score, method, inv_price, cand_price
            ) in normalized
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        out = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                out.append({
                    "is_correct": True,
                    "reason": f"exception:{r}",
                    "confidence": 0.0,
                    "row_idx": normalized[i][3],
                })
            else:
                r["row_idx"] = normalized[i][3]
                out.append(r)
        return out

    async def review_one(
        self, drug_a: str, drug_b: str,
        first_decision: str, first_confidence: float, first_reason: str,
        api_failed: bool = False, drug_b_ar: str = "",
        inventory_price=None, candidate_price=None,
    ) -> dict[str, Any]:
        """Ask a second model to review the first AI's decision.

        If api_failed=True, the first AI never made a real decision — ask for fresh verification.
        Returns {is_correct, reason, confidence}."""
        return await self._reviewer.review_one(
            drug_a, drug_b, first_decision, first_confidence, first_reason,
            api_failed, drug_b_ar, inventory_price, candidate_price,
        )

    async def review_batch(
        self, items: list[tuple]
    ) -> list[dict[str, Any]]:
        """Review a batch of first-AI decisions."""
        return await self._reviewer.review_batch(items)

    async def find_better_match(
        self, drug_name: str, candidates: list[tuple[dict, float, int]],
        inventory_price=None,
    ) -> dict[str, Any] | None:
        """Ask AI to pick the best match from candidates."""
        return await self._searcher.find_better_match(
            drug_name, candidates, inventory_price,
        )
