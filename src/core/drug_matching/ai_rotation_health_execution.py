"""Health check execution logic for rotated AI attempts."""

import asyncio

import aiohttp

from .ai_health import AIKey, test_one
from .ai_rotation import AIModelAttempt
from .ai_rotation_health_scoring import rank_health_rows


async def run_rotation_health(
    attempts: tuple[AIModelAttempt, ...],
    modes: list[str],
    timeout_s: float,
    max_tokens: int,
    concurrency: int,
) -> list[dict]:
    """Execute health checks for all rotation attempts and return ranked results."""
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        sem = asyncio.Semaphore(concurrency)

        async def guarded(attempt: AIModelAttempt, mode: str):
            async with sem:
                row = await test_one(
                    session,
                    AIKey(attempt.key_name, attempt.api_key),
                    attempt.model,
                    mode,
                    timeout_s,
                    max_tokens,
                    attempt.base_url,
                )
                row["provider"] = attempt.provider
                row["quality_rank"] = attempt.quality_rank
                row["rotation_tier"] = attempt.rotation_tier
                row["key_suffix"] = attempt.key_suffix
                return row

        tasks = [
            guarded(attempt, mode)
            for attempt in attempts
            for mode in modes
        ]
        return rank_health_rows(await asyncio.gather(*tasks))
