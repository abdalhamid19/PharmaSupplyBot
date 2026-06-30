"""Request building and API call execution for AI verifier.

This module provides the main interface for API calling with retry and fallback
logic, and re-exports components from submodules.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp

from ..config import APIConfig
from .verifier_core import fallback_from_unparseable_response
from .verifier_request_build import RequestPlanner as _RequestPlanner, RotationManager
from .verifier_request_parse import ResponseHandler
from .verifier_request_validate import FailureTracker

if TYPE_CHECKING:
    pass


class APICaller:
    """Handles API call execution with retry and fallback logic."""

    def __init__(self, planner: _RequestPlanner, failure_tracker: FailureTracker):
        self._planner = planner
        self._failure_tracker = failure_tracker
        self._response_handler = ResponseHandler(planner, failure_tracker)

    async def call_api(
        self, session: aiohttp.ClientSession | None, payload: dict,
        max_retries: int = 2,
    ) -> dict[str, Any] | None:
        """Make an API call with key+model fallback.
        Tries each (key, model) combination from the attempt plan.
        Returns parsed result dict or None if all attempts fail."""
        cfg = self._planner._cfg
        if not cfg.api_key:
            return None
        session, close_session = self._ensure_session(session)
        model = payload.get("model", cfg.model)
        plan = self._planner.build_request_plan(model)
        attempts = []
        last_unparseable: tuple[str, str] | None = None

        try:
            last_unparseable = await self._execute_request_plan(
                plan, payload, session, attempts, max_retries, last_unparseable
            )
            if last_unparseable:
                return self._build_fallback_response(last_unparseable, attempts)
            return None
        finally:
            if close_session and session:
                await session.close()

    def _ensure_session(self, session):
        """Ensure a valid session exists, creating one if needed."""
        if session is not None:
            return session, False
        session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "HTTP-Referer": "https://pharmasupplybot.local",
                "X-Title": "MediCompare Drug Matcher",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return session, True

    async def _execute_request_plan(
        self, plan, payload, session, attempts, max_retries, last_unparseable
    ):
        """Execute the request plan across all attempts."""
        for plan_idx, item in enumerate(plan):
            last_unparseable = await self._try_plan_item(
                item, payload, session, attempts, max_retries, plan_idx, last_unparseable
            )
        return last_unparseable

    async def _try_plan_item(
        self, item, payload, session, attempts, max_retries, plan_idx, last_unparseable
    ):
        """Try a single plan item with retries."""
        key = item["key"]
        mdl = item["model"]
        base_url = item["base_url"]
        provider = item["provider"]
        combo_key = self._planner.combo_key(key, mdl, provider)
        if combo_key in self._planner._failed_combos:
            return last_unparseable
        payload["model"] = mdl
        headers = dict(session.headers)
        headers["Authorization"] = f"Bearer {key}"

        for attempt in range(max_retries + 1):
            async with self._planner._semaphore:
                if combo_key in self._planner._failed_combos:
                    break
                result = await self._make_single_request(
                    session, base_url, payload, headers,
                    key, mdl, provider, plan_idx, attempt, attempts
                )
                if result is not None:
                    if result.get("parse_failed"):
                        last_unparseable = (result.get("content", ""), mdl)
                        break
                    self._planner.record_rotation_used(item)
                    return None
        return last_unparseable

    async def _make_single_request(
        self, session, base_url, payload, headers,
        key, mdl, provider, plan_idx, attempt, attempts
    ):
        """Make a single API request and handle response."""
        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                return await self._response_handler.handle_response(
                    resp, key, mdl, provider, plan_idx, attempt, attempts
                )
        except Exception as e:
            disabled = self._failure_tracker.record_combo_failure(
                key, mdl, type(e).__name__, provider=provider,
            )
            attempts.append({
                "attempt": attempt + 1, "provider": provider,
                "key_suffix": key[-6:], "model": mdl, "status": "exception",
                "fallback_used": plan_idx > 0,
                "decision": "disabled" if disabled else "failed",
                "error_stage": "api", "error_code": type(e).__name__,
                "reason": str(e)[:200],
            })
            self._failure_tracker.log_combo_failure(
                key, mdl, f"Exception {type(e).__name__}", str(e),
                provider=provider,
            )
            return None

    def _build_fallback_response(self, last_unparseable, attempts):
        """Build a fallback response from unparseable content."""
        content, mdl = last_unparseable
        parsed = fallback_from_unparseable_response(content, mdl)
        parsed["provider_used"] = attempts[-1].get("provider", "")
        parsed["_api_attempts"] = attempts
        return parsed


class PublicRequestPlanner:
    """Public interface for request planning with API caller and failure tracking."""

    def __init__(self, cfg: APIConfig, semaphore: asyncio.Semaphore):
        self._cfg = cfg
        self._semaphore = semaphore
        self._request_planner = _RequestPlanner(cfg, semaphore)
        self._failure_tracker = FailureTracker(self._request_planner)
        self._api_caller = APICaller(self._request_planner, self._failure_tracker)

    async def call_api(
        self, session: aiohttp.ClientSession | None, payload: dict,
        max_retries: int = 2,
    ) -> dict[str, Any] | None:
        """Make an API call with key+model fallback.
        Tries each (key, model) combination from the attempt plan.
        Returns parsed result dict or None if all attempts fail."""
        return await self._api_caller.call_api(session, payload, max_retries)

    def record_combo_failure(
        self, key: str, model: str, reason: str,
        *, permanent: bool = False, provider: str = "",
    ) -> bool:
        """Track failures and disable noisy key/model combos for this run."""
        return self._failure_tracker.record_combo_failure(
            key, model, reason, permanent=permanent, provider=provider
        )

    def log_combo_failure(
        self, key: str, model: str, reason: str, detail: str = "",
        provider: str = "",
    ) -> None:
        """Log API failure details."""
        self._failure_tracker.log_combo_failure(key, model, reason, detail, provider)

    def get_fallback_log(self) -> str:
        """Return and clear the API failure log for trace reporting."""
        return self._request_planner.get_fallback_log()


# Backward compatibility alias
RequestPlanner = PublicRequestPlanner

# Re-export all public components
__all__ = [
    "RequestPlanner",
    "PublicRequestPlanner",
    "FailureTracker",
    "RotationManager",
    "ResponseHandler",
    "APICaller",
]
