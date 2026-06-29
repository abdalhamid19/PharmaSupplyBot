"""Request building and API call execution for AI verifier.

This module consolidates request planning, rotation management, API calling,
failure tracking, and response handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from .config import APIConfig
from .verifier_core import (
    _PERMANENT_PARSE_FAILURES,
    _TRANSIENT_COMBO_FAILURE_LIMIT,
    api_error_code,
    extract_json,
    fallback_from_unparseable_response,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger("pharmasupplybot.matching")

class FailureTracker:
    """Manages API failure tracking and logging."""

    def __init__(self, planner):
        self._planner = planner

    def record_combo_failure(
        self, key: str, model: str, reason: str,
        *, permanent: bool = False, provider: str = "",
    ) -> bool:
        """Track failures and disable noisy key/model combos for this run."""
        combo = self._planner.combo_key(key, model, provider)
        if permanent:
            self._planner._failed_combos.add(combo)
            return True
        count = self._planner._combo_failures.get(combo, 0) + 1
        self._planner._combo_failures[combo] = count
        if count >= _TRANSIENT_COMBO_FAILURE_LIMIT:
            self._planner._failed_combos.add(combo)
            return True
        return False

    def log_combo_failure(
        self, key: str, model: str, reason: str, detail: str = "",
        provider: str = "",
    ) -> None:
        detail_text = f": {detail[:160]}" if detail else ""
        provider_text = f" provider={provider}" if provider else ""
        log_msg = (
            f"{reason}{detail_text} with{provider_text} "
            f"model={model} key=...{key[-6:]}"
        )
        self._planner._fallback_log.append(log_msg)
        logger.warning("  ⚠ %s, trying next...", log_msg)


class RotationManager:
    """Manages rotation logic for API request planning."""

    def __init__(self, planner):
        self._planner = planner

    def rotation_request_plan(self, requested_model: str = "") -> list[dict[str, Any]]:
        attempts = self.rotation_attempts_for(requested_model)
        plan = []
        for tier in sorted({attempt.rotation_tier for attempt in attempts}):
            tier_attempts = [
                attempt for attempt in attempts
                if attempt.rotation_tier == tier
                and self._planner.combo_key(
                    attempt.api_key, attempt.model, attempt.provider,
                ) not in self._planner._failed_combos
            ]
            plan.extend(
                self.rotated_tier_plan(
                    tier_attempts, requested_model, tier,
                    advance=not plan,
                ),
            )
        return plan

    def rotation_attempts_for(self, requested_model: str = ""):
        attempts = self._planner._cfg.attempt_plan
        if requested_model == "rotation" and self._planner._cfg.review_attempt_plan:
            return self.strong_enough_review_attempts(
                self._planner._cfg.review_attempt_plan,
            )
        elif requested_model and requested_model != self._planner._cfg.model:
            matching = tuple(
                attempt for attempt in attempts
                if attempt.model == requested_model
            )
            if matching:
                return self.strong_enough_review_attempts(matching)
        return attempts

    def strong_enough_review_attempts(self, attempts):
        primary = self.primary_rotation_attempt()
        if primary is None:
            return tuple(attempts)
        primary_strength = self.attempt_strength(primary)
        return tuple(
            attempt for attempt in attempts
            if self.attempt_strength(attempt) <= primary_strength
        )

    def primary_rotation_attempt(self):
        for attempt in self._planner._cfg.attempt_plan:
            if attempt.model == self._planner._cfg.model:
                return attempt
        return self._planner._cfg.attempt_plan[0] if self._planner._cfg.attempt_plan else None

    @staticmethod
    def attempt_strength(attempt) -> tuple[int, int]:
        return attempt.rotation_tier, attempt.quality_rank

    def rotated_tier_plan(
        self, attempts, requested_model: str, tier: int, *, advance: bool,
    ) -> list[dict[str, Any]]:
        if not attempts:
            return []
        key = self.rotation_cursor_key(requested_model, tier)
        start = self._planner._rotation_cursors.get(key, 0) % len(attempts)
        if advance:
            self._planner._rotation_cursors[key] = (start + 1) % len(attempts)
        indexed = list(enumerate(attempts))
        ordered = indexed[start:] + indexed[:start]
        return [
            self.rotation_plan_item(attempt, key, position, len(attempts))
            for position, attempt in ordered
        ]

    def rotation_plan_item(
        self, attempt, cursor_key: str, position: int, count: int,
    ) -> dict[str, Any]:
        return {
            "provider": attempt.provider,
            "base_url": attempt.base_url,
            "key": attempt.api_key,
            "model": attempt.model,
            "rotation_cursor_key": cursor_key,
            "rotation_position": position,
            "rotation_count": count,
            "rotation_tier": attempt.rotation_tier,
        }

    def rotation_cursor_key(self, requested_model: str, tier: int) -> str:
        if requested_model == "rotation" and self._planner._cfg.review_attempt_plan:
            scope = "review"
        elif requested_model and requested_model != self._planner._cfg.model:
            scope = f"model:{requested_model}"
        else:
            scope = "primary"
        return f"{scope}:tier:{tier}"

    def record_rotation_used(self, item: dict[str, Any]) -> None:
        key = item.get("rotation_cursor_key")
        position = item.get("rotation_position")
        count = item.get("rotation_count")
        if key is None or position is None or not count:
            return
        self._planner._rotation_cursors[str(key)] = (int(position) + 1) % int(count)

class RequestPlanner:
    """Manages API request planning and attempt strategies."""

    def __init__(self, cfg, semaphore):
        self._cfg = cfg
        self._semaphore = semaphore
        self._failed_combos: set[tuple[str, str]] = set()
        self._combo_failures: dict[tuple[str, str], int] = {}
        self._rotation_cursors: dict[str, int] = {}
        self._fallback_log: list[str] = []
        self._rotation_manager = RotationManager(self)

    def get_fallback_log(self) -> str:
        """Return and clear the API failure log for trace reporting."""
        if not self._fallback_log:
            return ""
        log = "; ".join(self._fallback_log)
        self._fallback_log.clear()
        return log

    def build_attempt_plan(self, model: str) -> list[tuple[str, str]]:
        """Build ordered list of (api_key, model) to try, skipping previously failed combos.
        Order: primary key + primary model -> other keys + primary model -> fallback
        models + all keys."""
        keys = self._cfg.api_keys if self._cfg.api_keys else (self._cfg.api_key,)
        models = [model] + list(self._cfg.fallback_models)
        healthy = set(self._cfg.healthy_combos or ())
        plan = []
        for key in keys:
            combo = (key[-6:], models[0])
            if combo not in self._failed_combos and (not healthy or combo in healthy):
                plan.append((key, models[0]))
        for mdl in models[1:]:
            for key in keys:
                combo = (key[-6:], mdl)
                if combo not in self._failed_combos and (not healthy or combo in healthy):
                    plan.append((key, mdl))
        return plan

    def build_request_plan(self, model: str) -> list[dict[str, Any]]:
        if self._cfg.attempt_plan:
            return self._rotation_manager.rotation_request_plan(model)
        return [
            {"provider": "default", "base_url": self._cfg.base_url, "key": key, "model": mdl}
            for key, mdl in self.build_attempt_plan(model)
        ]

    def record_rotation_used(self, item: dict[str, Any]) -> None:
        self._rotation_manager.record_rotation_used(item)

    @staticmethod
    def combo_key(key: str, model: str, provider: str = ""):
        if provider:
            return provider, key[-6:], model
        return key[-6:], model

class ResponseHandler:
    """Handles API response processing and error handling."""

    def __init__(self, planner: RequestPlanner, failure_tracker: FailureTracker):
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
            "attempt": attempt + 1, "provider": provider, "key_suffix": key[-6:],
            "model": mdl, "status": resp.status, "fallback_used": plan_idx > 0,
            "decision": "disabled" if disabled else "failed", "error_stage": "api",
            "error_code": "rate_limited", "reason": f"429 retry_after={retry_after or '10'}",
        })
        self._failure_tracker.log_combo_failure(
            key, mdl, "Rate limited", attempts[-1]["reason"], provider=provider,
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
            permanent=(resp.status in (401, 403) or error_code == "json_generation_failed"),
            provider=provider,
        )
        attempts.append({
            "attempt": attempt + 1, "provider": provider, "key_suffix": key[-6:],
            "model": mdl, "status": resp.status, "fallback_used": plan_idx > 0,
            "decision": "disabled" if disabled else "failed", "error_stage": "api",
            "error_code": error_code, "reason": text[:200],
        })
        log_reason = (
            "JSON generation failed"
            if error_code == "json_generation_failed"
            else f"API error {resp.status}"
        )
        self._failure_tracker.log_combo_failure(key, mdl, log_reason, text, provider=provider)
        return None

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
            "attempt": attempt + 1, "provider": provider, "key_suffix": key[-6:],
            "model": mdl, "status": 200, "fallback_used": plan_idx > 0,
            "decision": "success", "reason": "parsed_json",
        })
        self._planner._combo_failures.pop(self._planner.combo_key(key, mdl, provider), None)
        confidence = float(result.get("confidence", 0.0))
        if confidence == 0.0:
            is_correct = bool(result.get("is_correct", False))
            confidence = 0.7 if is_correct else 0.6
        return {
            "is_correct": bool(result.get("is_correct", False)),
            "agree": bool(result.get("agree", True)),
            "reason": str(result.get("reason", "")),
            "confidence": confidence, "model_used": mdl, "provider_used": provider,
            "decision": str(result.get("decision", "")),
            "hard_conflicts": result.get("hard_conflicts", []),
            "matched_fields": result.get("matched_fields", []),
            "mismatched_fields": result.get("mismatched_fields", []),
            "_raw": result, "_api_attempts": attempts,
        }

    def _handle_parse_failure(
        self, content, content_text: str, key: str, mdl: str, provider: str,
        plan_idx: int, attempt: int, attempts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Handle JSON parse failures from successful API responses."""
        error_code = "null_content" if content is None else "invalid_json"
        disabled = self._failure_tracker.record_combo_failure(
            key, mdl, error_code,
            permanent=error_code in _PERMANENT_PARSE_FAILURES,
            provider=provider,
        )
        attempts.append({
            "attempt": attempt + 1, "provider": provider, "key_suffix": key[-6:],
            "model": mdl, "status": 200, "fallback_used": plan_idx > 0,
            "decision": "disabled" if disabled else "parse_failed", "error_stage": "ai_parse",
            "error_code": error_code, "parse_failed": True,
            "reason": content_text[:200], "content": content_text,
        })
        logger.warning("  ⚠ %s from model=%s", error_code, mdl)
        return {"parse_failed": True, "content": content_text}

class APICaller:
    """Handles API call execution with retry and fallback logic."""

    def __init__(self, planner: RequestPlanner, failure_tracker: FailureTracker):
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
                            break
            if last_unparseable:
                content, mdl = last_unparseable
                parsed = fallback_from_unparseable_response(content, mdl)
                parsed["provider_used"] = attempts[-1].get("provider", "")
                parsed["_api_attempts"] = attempts
                return parsed
            return None
        finally:
            if close_session and session:
                await session.close()

class PublicRequestPlanner:
    """Public interface for request planning with API caller and failure tracking."""

    def __init__(self, cfg: APIConfig, semaphore: asyncio.Semaphore):
        self._cfg = cfg
        self._semaphore = semaphore
        self._request_planner = RequestPlanner(cfg, semaphore)
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


RequestPlanner = PublicRequestPlanner

__all__ = [
    "RequestPlanner",
    "PublicRequestPlanner",
    "FailureTracker",
    "RotationManager",
    "ResponseHandler",
    "APICaller",
]
