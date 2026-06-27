"""Request building and attempt planning for AI verifier."""

import asyncio
from typing import Any

import aiohttp

from .config import APIConfig
from .verifier_request_api import APICaller
from .verifier_request_failure import FailureTracker
from .verifier_request_planning import RequestPlanner as BaseRequestPlanner


class RequestPlanner(BaseRequestPlanner):
    """Manages API request planning and attempt strategies."""

    def __init__(self, cfg: APIConfig, semaphore: asyncio.Semaphore):
        super().__init__(cfg, semaphore)
        self._failure_tracker = FailureTracker(self)
        self._api_caller = APICaller(self, self._failure_tracker)

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
        self._failure_tracker.log_combo_failure(
            key, model, reason, detail, provider
        )
