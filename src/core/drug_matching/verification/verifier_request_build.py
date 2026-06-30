"""Request building and planning for AI verifier API calls.

This module handles request planning, rotation management, and attempt strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


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
        """Build ordered list of (api_key, model) to try, skipping failed combos.
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


__all__ = ["RequestPlanner", "RotationManager"]
