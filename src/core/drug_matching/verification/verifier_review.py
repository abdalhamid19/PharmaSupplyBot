"""Review path for AI verifier - second-opinion verification."""

import asyncio
from typing import Any

from ..config import APIConfig
from ..pricing import price_context
from ..prompts import FRESH_REVIEW_PROMPT, REVIEW_PROMPT, SYSTEM_PROMPT, render_prompt
from .verifier_helpers import component_context, normalize_review_item
from .verifier_request import RequestPlanner
from .verifier_response import process_api_response


class ReviewVerifier:
    """Handles second-opinion AI verification."""

    def __init__(self, cfg: APIConfig, planner: RequestPlanner):
        self._cfg = cfg
        self._planner = planner

    async def review_one(
        self, drug_a: str, drug_b: str,
        first_decision: str, first_confidence: float, first_reason: str,
        api_failed: bool = False, drug_b_ar: str = "",
        inventory_price=None, candidate_price=None,
    ) -> dict[str, Any]:
        """Ask a second model to review the first AI's decision.
        If api_failed=True, the first AI never made a real decision — ask for fresh verification.
        Returns {is_correct, reason, confidence}."""
        review_model = self._cfg.review_model
        if not review_model or (not self._cfg.api_keys and not self._cfg.api_key):
            return {"is_correct": True, "reason": "no_review_model", "confidence": first_confidence}

        ar_line = f"\nDRUG B Arabic: {drug_b_ar}" if drug_b_ar else ""
        if api_failed:
            prompt = render_prompt(
                FRESH_REVIEW_PROMPT,
                drug_a=drug_a,
                drug_b=drug_b,
                drug_b_ar_line=ar_line,
                drug_a_context=component_context(drug_a),
                drug_b_context=component_context(drug_b),
                price_context=price_context(inventory_price, candidate_price),
            )
        else:
            decision_text = (
                "CORRECT match"
                if first_decision in {"ai_confirmed", "ai_corrected", "ai_found"}
                else "INCORRECT match"
            )
            prompt = render_prompt(
                REVIEW_PROMPT,
                drug_a=drug_a,
                drug_b=drug_b,
                drug_b_ar_line=ar_line,
                drug_a_context=component_context(drug_a),
                drug_b_context=component_context(drug_b),
                price_context=price_context(inventory_price, candidate_price),
                first_decision_text=decision_text,
                first_confidence=first_confidence,
                first_reason=first_reason,
            )

        payload = {
            "model": review_model,
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
            return {"is_correct": True, "reason": "review_all_api_failed", "confidence": first_confidence}

        if result.get("parse_failed"):
            return {
                "is_correct": not api_failed,
                "reason": str(result.get("reason", "invalid_json")),
                "confidence": min(float(result.get("confidence", 0.0)), 0.5),
                "parse_failed": True,
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
            }

        if api_failed:
            # Fresh verification: result is direct is_correct
            return {
                "is_correct": bool(result.get("is_correct", True)),
                "reason": str(result.get("reason", "")),
                "confidence": float(result.get("confidence", first_confidence)),
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
            }
        agree = bool(result.get("agree", True))
        # Resolve decision vs agree contradiction
        review_decision = str(result.get("decision", "")).lower().strip()
        if review_decision == "disagree" and agree:
            agree = False
        elif review_decision == "agree" and not agree:
            agree = True
        first_ai_said_correct = first_decision in {
            "ai_confirmed", "ai_corrected", "ai_found",
        }
        review_result = {
            "is_correct": agree if first_ai_said_correct else not agree,
            "reason": str(result.get("reason", "")),
            "confidence": float(result.get("confidence", first_confidence)),
            "model_used": result.get("model_used", ""),
            "provider_used": result.get("provider_used", ""),
            "hard_conflicts": result.get("hard_conflicts", []),
            "_api_attempts": result.get("_api_attempts", []),
        }
        # Apply hard_conflicts logic to review result as well
        return process_api_response(review_result)

    async def review_batch(
        self, items: list[tuple]
    ) -> list[dict[str, Any]]:
        """Review a batch of first-AI decisions."""
        normalized = [normalize_review_item(item) for item in items]
        tasks = [
            self.review_one(
                a, b, d, c, r, api_failed=f, drug_b_ar=ar,
                inventory_price=inv_price, candidate_price=cand_price,
            )
            for (
                a, b, ar, d, c, r, _, f, inv_price, cand_price
            ) in normalized
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                out.append({
                    "is_correct": True,
                    "reason": f"review_exception:{r}",
                    "confidence": normalized[i][4],
                    "row_idx": normalized[i][6],
                })
            else:
                r["row_idx"] = normalized[i][6]
                out.append(r)
        return out
