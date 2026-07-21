"""AI review execution logic - batch processing and result application."""

import logging
import pandas as pd

from ..config import MatchingConfig
from ..verification.verifier import AIVerifier
from .ai_review_result_applier import ReviewResultApplier

logger = logging.getLogger(__name__)

_AI_REVIEW_OVERRIDE_CONFIDENCE = 0.75


async def _batch_review(verifier, items, cfg):
    """Review a batch of items with the second model."""
    all_results = []
    batch_size = cfg.ai_batch_size
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results = await verifier.review_batch(batch)
        # Propagate api_failed flag from items to results
        for j, r in enumerate(results):
            r["api_failed"] = batch[j][7]
        all_results.extend(results)
        done = min(i + batch_size, len(items))
        logger.info(f"  Reviewed {done}/{len(items)}")
    return all_results


async def _apply_review_results(
    verifier, results, index, all_results, cfg, trace,
):
    """Apply review results: if second model disagrees, re-evaluate.
    For api_failed items, is_correct is a direct fresh decision."""
    applier = ReviewResultApplier(verifier, results, index, cfg, trace)
    return await applier.apply_results(all_results)
