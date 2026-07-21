"""Batch processing for AI search core."""

from __future__ import annotations

import asyncio
import logging

from .ai_search_core_execution import _try_search_one
from .ai_search_trace import _trace_search_exception

logger = logging.getLogger(__name__)


async def _search_batch(verifier, results, index, unmatched, cfg, trace):
    """Search for matches in batches."""
    found = 0
    batch_size = cfg.ai_batch_size
    items = list(unmatched.iterrows())
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        raw_results = await asyncio.gather(*[
            _try_search_one(verifier, results, index, row, cfg, trace)
            for _, row in batch
        ], return_exceptions=True)
        batch_results = []
        for (_, row), item in zip(batch, raw_results):
            if isinstance(item, Exception):
                logger.warning(
                    "  ⚠ AI search exception for row=%s: %s",
                    row.name, item,
                )
                _trace_search_exception(trace, row, item)
                batch_results.append(0)
            else:
                batch_results.append(item)
        found += sum(batch_results)
        done = min(i + batch_size, len(items))
        logger.info(f"  Searched {done}/{len(items)}, found {found}")
    return found


__all__ = ["_search_batch"]
