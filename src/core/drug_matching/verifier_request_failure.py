"""Failure tracking and logging for AI verifier requests."""

import logging

_TRANSIENT_COMBO_FAILURE_LIMIT = 2

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
