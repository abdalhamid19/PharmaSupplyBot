"""Search path for AI verifier - finding best match from candidates."""

from typing import Any

from ..config import APIConfig
from ..pricing import format_price
from ..prompts import SEARCH_PROMPT, SYSTEM_PROMPT, render_prompt
from .verifier_helpers import coerce_best_index, component_context, format_candidate
from .verifier_request import RequestPlanner
from .verifier_response import process_api_response


class SearchVerifier:
    """Handles AI-powered candidate selection."""

    def __init__(self, cfg: APIConfig, planner: RequestPlanner):
        self._cfg = cfg
        self._planner = planner

    async def find_better_match(
        self, drug_name: str, candidates: list[tuple[dict, float, int]],
        inventory_price=None,
    ) -> dict[str, Any] | None:
        """Ask AI to pick the best match from candidates."""
        if not candidates or (not self._cfg.api_keys and not self._cfg.api_key):
            return None

        candidates_text = "\n".join(
            format_candidate(i + 1, c, inventory_price)
            for i, c in enumerate(candidates[:5])
        )
        prompt = render_prompt(
            SEARCH_PROMPT,
            drug_name=drug_name,
            inventory_context=component_context(drug_name),
            inventory_price=format_price(inventory_price),
            candidates_text=candidates_text,
            max_index=min(len(candidates), 5),
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

        result = await self._planner.call_api(None, payload)
        if result is None:
            return None
        raw = result.get("_raw", {})
        raw_best_index = raw.get("best_index", 0)
        max_index = min(len(candidates), 5)
        best_idx, valid_index = coerce_best_index(raw_best_index, max_index)
        if not valid_index:
            return {
                "record": None, "score": 0.0,
                "reason": f"invalid_best_index:{str(raw_best_index)[:80]}",
                "confidence": min(float(result.get("confidence", 0.0)), 0.5),
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
                "best_index": 0,
                "parse_failed": True,
                "error_code": "invalid_best_index",
            }
        if best_idx > 0:
            return {
                "record": candidates[best_idx - 1][0],
                "score": candidates[best_idx - 1][1],
                "reason": result.get("reason", ""),
                "confidence": float(result.get("confidence", 0.0)),
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
                "best_index": best_idx,
                "parse_failed": result.get("parse_failed", False),
            }
        return {
            "record": None, "score": 0.0,
            "reason": result.get("reason", "none"),
            "confidence": float(result.get("confidence", 0.0)),
            "model_used": result.get("model_used", ""),
            "provider_used": result.get("provider_used", ""),
            "_api_attempts": result.get("_api_attempts", []),
            "best_index": best_idx,
            "parse_failed": result.get("parse_failed", False),
        }
