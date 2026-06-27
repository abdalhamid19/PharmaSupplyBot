"""Request planning and rotation logic for AI verifier."""

from typing import Any

from .verifier_request_rotation import RotationManager


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
        Order: primary key + primary model → other keys + primary model → fallback models + all keys."""
        keys = self._cfg.api_keys if self._cfg.api_keys else (self._cfg.api_key,)
        models = [model] + list(self._cfg.fallback_models)
        healthy = set(self._cfg.healthy_combos or ())
        plan = []
        # Phase 1: try primary model with all keys
        for key in keys:
            combo = (key[-6:], models[0])
            if combo not in self._failed_combos and (not healthy or combo in healthy):
                plan.append((key, models[0]))
        # Phase 2: try each fallback model with all keys
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
            {
                "provider": "default",
                "base_url": self._cfg.base_url,
                "key": key,
                "model": mdl,
            }
            for key, mdl in self.build_attempt_plan(model)
        ]

    def record_rotation_used(self, item: dict[str, Any]) -> None:
        self._rotation_manager.record_rotation_used(item)

    @staticmethod
    def combo_key(key: str, model: str, provider: str = ""):
        if provider:
            return provider, key[-6:], model
        return key[-6:], model
