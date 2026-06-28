"""Success response handlers for API 200 responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .verifier_helpers import extract_json

if TYPE_CHECKING:
    from .verifier_request_planning import RequestPlanner


class SuccessResponseHandlers:
    """Mix-in methods for success response handling."""

    async def _handle_success_response(
        self, resp, key: str, mdl: str, provider: str,
        plan_idx: int, attempt: int, attempts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle successful 200 responses."""
        data = await resp.json()
        content = data["choices"][0]["message"].get("content")
        content_text = content if isinstance(content, str) else ""
        result = extract_json(content)
        if result is None:
            return self._handle_parse_failure(
                content, content_text, key, mdl, provider, plan_idx, attempt, attempts
            )
        attempts.append({
            "attempt": attempt + 1,
            "provider": provider,
            "key_suffix": key[-6:],
            "model": mdl,
            "status": 200,
            "fallback_used": plan_idx > 0,
            "decision": "success",
            "reason": "parsed_json",
        })
        self._planner._combo_failures.pop(
            self._planner.combo_key(key, mdl, provider), None,
        )
        confidence = float(result.get("confidence", 0.0))
        if confidence == 0.0:
            is_correct = bool(result.get("is_correct", False))
            confidence = 0.7 if is_correct else 0.6
        return {
            "is_correct": bool(result.get("is_correct", False)),
            "agree": bool(result.get("agree", True)),
            "reason": str(result.get("reason", "")),
            "confidence": confidence,
            "model_used": mdl,
            "provider_used": provider,
            "decision": str(result.get("decision", "")),
            "hard_conflicts": result.get("hard_conflicts", []),
            "matched_fields": result.get("matched_fields", []),
            "mismatched_fields": result.get("mismatched_fields", []),
            "_raw": result,
            "_api_attempts": attempts,
        }


__all__ = ["SuccessResponseHandlers"]
