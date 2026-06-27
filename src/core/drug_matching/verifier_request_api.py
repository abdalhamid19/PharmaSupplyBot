"""API call execution logic for AI verifier."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from .config import APIConfig
from .verifier_helpers import fallback_from_unparseable_response
from .verifier_request_failure import FailureTracker
from .verifier_request_response import ResponseHandler

if TYPE_CHECKING:
    from .verifier_request_planning import RequestPlanner

logger = logging.getLogger("pharmasupplybot.matching")


class APICaller:
    """Handles API call execution with retry and fallback logic."""

    def __init__(self, planner: "RequestPlanner", failure_tracker: FailureTracker):
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
        close_session = False
        if session is None:
            session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://pharmasupplybot.local",
                    "X-Title": "MediCompare Drug Matcher",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            )
            close_session = True
        model = payload.get("model", cfg.model)
        plan = self._planner.build_request_plan(model)
        attempts = []
        last_unparseable: tuple[str, str] | None = None

        try:
            for plan_idx, item in enumerate(plan):
                key = item["key"]
                mdl = item["model"]
                base_url = item["base_url"]
                provider = item["provider"]
                combo_key = self._planner.combo_key(key, mdl, provider)
                if combo_key in self._planner._failed_combos:
                    continue
                payload["model"] = mdl
                headers = dict(session.headers)
                headers["Authorization"] = f"Bearer {key}"

                for attempt in range(max_retries + 1):
                    async with self._planner._semaphore:
                        if combo_key in self._planner._failed_combos:
                            break
                        try:
                            async with session.post(
                                f"{base_url}/chat/completions",
                                json=payload,
                                headers=headers,
                            ) as resp:
                                result = await self._response_handler.handle_response(
                                    resp, key, mdl, provider, plan_idx, attempt, attempts
                                )
                                if result is not None:
                                    if result.get("parse_failed"):
                                        last_unparseable = (result.get("content", ""), mdl)
                                        break
                                    self._planner.record_rotation_used(item)
                                    return result
                        except Exception as e:
                            disabled = self._failure_tracker.record_combo_failure(
                                key, mdl, type(e).__name__,
                                provider=provider,
                            )
                            attempts.append({
                                "attempt": attempt + 1,
                                "provider": provider,
                                "key_suffix": key[-6:],
                                "model": mdl,
                                "status": "exception",
                                "fallback_used": plan_idx > 0,
                                "decision": "disabled" if disabled else "failed",
                                "error_stage": "api",
                                "error_code": type(e).__name__,
                                "reason": str(e)[:200],
                            })
                            self._failure_tracker.log_combo_failure(
                                key, mdl, f"Exception {type(e).__name__}",
                                str(e),
                                provider=provider,
                            )
                            break  # try next combo
            if last_unparseable:
                content, mdl = last_unparseable
                parsed = fallback_from_unparseable_response(content, mdl)
                parsed["provider_used"] = attempts[-1].get("provider", "")
                parsed["_api_attempts"] = attempts
                return parsed
            return None  # all combos exhausted
        finally:
            if close_session and session:
                await session.close()
