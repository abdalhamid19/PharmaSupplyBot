"""AIVerifier method implementations."""

from __future__ import annotations

import asyncio
from typing import Any

from ..config import APIConfig
from ..pricing import price_context
from ..prompts import SYSTEM_PROMPT, VERIFY_PROMPT, render_prompt
from .verifier_helpers import (
    component_context,
    normalize_verify_item,
)
from .verifier_response import process_api_response


class AIVerifierMethods:
    """Mix-in methods for AIVerifier class."""

    async def verify_one(
        self, drug_a: str, drug_b: str, drug_b_ar: str = "",
        algo_score="", algo_method="", inventory_price=None,
        candidate_price=None,
    ) -> dict[str, Any]:
        """Verify a single match. Returns {is_correct, reason, confidence}."""
        cfg = self._cfg
        if not cfg.api_key:
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
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "response_format": {"type": "json_object"},
        }

        result = await self._planner.call_api(self._session, payload)
        if result is None:
            return {
                "is_correct": True,
                "reason": "all_api_failed",
                "confidence": 0.0,
                "api_failed": True,
            }
        result.pop("agree", None)
        return process_api_response(result)

    async def verify_batch(self, matches: list[tuple]) -> list[dict[str, Any]]:
        """Verify a batch of matches. Each item is (drug_a, drug_b, drug_b_ar, row_index)."""
        normalized = [normalize_verify_item(item) for item in matches]
        tasks = [self._verify_task(item) for item in normalized]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._process_batch_results(results, normalized)

    async def _verify_task(self, item: tuple) -> dict[str, Any]:
        """Verify a single normalized item."""
        a, b, ar, _, score, method, inv_price, cand_price = item
        return await self.verify_one(a, b, ar, score, method, inv_price, cand_price)

    def _process_batch_results(self, results, normalized) -> list[dict[str, Any]]:
        """Process batch verification results."""
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
        """Ask a second model to review the first AI's decision."""
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


__all__ = ["AIVerifierMethods"]
