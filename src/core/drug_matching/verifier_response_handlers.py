"""Response handler methods for different API response types."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .verifier_response_error import ErrorResponseHandlers
from .verifier_response_success import SuccessResponseHandlers

if TYPE_CHECKING:
    from .verifier_request_failure import FailureTracker

logger = logging.getLogger("pharmasupplybot.matching")


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


__all__ = ["ResponseHandlerMethods"]
