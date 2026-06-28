"""Error response handlers for API rate limits and errors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .verifier_helpers import api_error_code

if TYPE_CHECKING:
    from .verifier_request_failure import FailureTracker

logger = logging.getLogger("pharmasupplybot.matching")


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


__all__ = ["ErrorResponseHandlers"]
