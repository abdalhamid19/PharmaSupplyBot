"""Response handling logic for AI verifier API calls."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .verifier_request_failure import FailureTracker
from .verifier_response_handlers import ResponseHandlerMethods

if TYPE_CHECKING:
    from .verifier_request_planning import RequestPlanner

logger = logging.getLogger("pharmasupplybot.matching")


class ResponseHandler(ResponseHandlerMethods):
    """Handles API response processing and error handling."""

    def __init__(self, planner: "RequestPlanner", failure_tracker: FailureTracker):
        self._planner = planner
        self._failure_tracker = failure_tracker

    async def handle_response(
        self, resp, key: str, mdl: str, provider: str,
        plan_idx: int, attempt: int, attempts: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Process API response and return parsed result or None on failure."""
        if resp.status == 429:
            return await self._handle_rate_limit(
                resp, key, mdl, provider, plan_idx, attempt, attempts
            )
        if resp.status != 200:
            return await self._handle_error_response(
                resp, key, mdl, provider, plan_idx, attempt, attempts
            )
        return await self._handle_success_response(
            resp, key, mdl, provider, plan_idx, attempt, attempts
        )


__all__ = ["ResponseHandler"]

