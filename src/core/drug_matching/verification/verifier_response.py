"""Response processing and conflict resolution for AI verifier."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .verifier_helpers import (
    api_error_code,
    apply_conflict_penalty,
    apply_critical_conflicts,
    apply_reject_decision_override,
    extract_json,
    hard_conflict_names,
    resolve_ai_conflicts,
)

if TYPE_CHECKING:
    from .verifier_request_validate import FailureTracker
    from .verifier_request_build import RequestPlanner

logger = logging.getLogger(__name__)


def process_api_response(result: dict[str, Any]) -> dict[str, Any]:
    """Process and resolve conflicts in AI API response.

    This is the main entry point for response processing, which:
    1. Detects and resolves contradictions in AI response fields
    2. Applies hard conflict overrides for critical mismatches
    3. Handles decision vs is_correct contradictions
    4. Caps confidence based on conflict types

    Args:
        result: Raw result from AI API call

    Returns:
        Processed result with conflicts resolved
    """
    return resolve_ai_conflicts(result)


def apply_conflict_logic(result: dict[str, Any]) -> dict[str, Any]:
    """Apply all conflict resolution logic to an AI result.

    This is an alias for resolve_ai_conflicts for clarity in calling code.
    """
    return resolve_ai_conflicts(result)


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


class ErrorResponseHandlers:
    """Mix-in methods for error response handling."""

    async def _handle_rate_limit(
        self, resp, key: str, mdl: str, provider: str,
        plan_idx: int, attempt: int, attempts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle 429 rate limit responses."""
        retry_after = resp.headers.get("Retry-After", "")
        disabled = self._failure_tracker.record_combo_failure(
            key, mdl, "rate_limited",
            permanent=bool(retry_after),
            provider=provider,
        )
        attempts.append({
            "attempt": attempt + 1,
            "provider": provider,
            "key_suffix": key[-6:],
            "model": mdl,
            "status": resp.status,
            "fallback_used": plan_idx > 0,
            "decision": "disabled" if disabled else "failed",
            "error_stage": "api",
            "error_code": "rate_limited",
            "reason": f"429 retry_after={retry_after or '10'}",
        })
        self._failure_tracker.log_combo_failure(
            key, mdl, "Rate limited",
            attempts[-1]["reason"],
            provider=provider,
        )
        return None

    async def _handle_error_response(
        self, resp, key: str, mdl: str, provider: str,
        plan_idx: int, attempt: int, attempts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle non-200 error responses."""
        text = await resp.text()
        error_code = api_error_code(resp.status, text)
        disabled = self._failure_tracker.record_combo_failure(
            key, mdl, error_code,
            permanent=(
                resp.status in (401, 403)
                or error_code == "json_generation_failed"
            ),
            provider=provider,
        )
        attempts.append({
            "attempt": attempt + 1,
            "provider": provider,
            "key_suffix": key[-6:],
            "model": mdl,
            "status": resp.status,
            "fallback_used": plan_idx > 0,
            "decision": "disabled" if disabled else "failed",
            "error_stage": "api",
            "error_code": error_code,
            "reason": text[:200],
        })
        log_reason = (
            "JSON generation failed"
            if error_code == "json_generation_failed"
            else f"API error {resp.status}"
        )
        self._failure_tracker.log_combo_failure(
            key, mdl, log_reason, text,
            provider=provider,
        )
        return None


class ResponseHandlerMethods(ErrorResponseHandlers, SuccessResponseHandlers):
    """Mix-in methods for ResponseHandler class."""

    def _handle_parse_failure(
        self, content, content_text: str, key: str, mdl: str, provider: str,
        plan_idx: int, attempt: int, attempts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle JSON parse failures from successful API responses."""
        error_code = "null_content" if content is None else "invalid_json"
        disabled = self._failure_tracker.record_combo_failure(
            key, mdl, error_code,
            permanent=error_code in ("invalid_json", "null_content", "json_generation_failed"),
            provider=provider,
        )
        attempts.append({
            "attempt": attempt + 1,
            "provider": provider,
            "key_suffix": key[-6:],
            "model": mdl,
            "status": 200,
            "fallback_used": plan_idx > 0,
            "decision": "disabled" if disabled else "parse_failed",
            "error_stage": "ai_parse",
            "error_code": error_code,
            "parse_failed": True,
            "reason": content_text[:200],
            "content": content_text,
        })
        logger.warning("  ⚠ %s from model=%s", error_code, mdl)
        return {"parse_failed": True, "content": content_text}


__all__ = [
    "process_api_response",
    "apply_conflict_logic",
    "resolve_ai_conflicts",
    "hard_conflict_names",
    "apply_critical_conflicts",
    "apply_conflict_penalty",
    "apply_reject_decision_override",
    "SuccessResponseHandlers",
    "ErrorResponseHandlers",
    "ResponseHandlerMethods",
]
