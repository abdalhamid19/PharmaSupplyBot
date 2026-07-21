"""AI search logic for finding matches among unmatched items."""

import logging

import pandas as pd

from ..config import MatchingConfig, APIConfig
from ..normalization.normalizer import parse_drug
from ..indexing.indexer import DrugIndex
from ..verification.verifier import AIVerifier
from .ai_search_core import _try_search_one, _search_batch
from .ai_search_trace import _trace_skip_all_search

logger = logging.getLogger(__name__)


def _get_unmatched(results):
    """Get unmatched items from results."""
    return results[
        (results["matched_product_name_en"].isna()) |
        (results["matched_product_name_en"] == "")
    ].copy()


async def run_ai_search(
    results: pd.DataFrame,
    index: DrugIndex,
    cfg: MatchingConfig,
    api_cfg: APIConfig,
    trace=None,
) -> pd.DataFrame:
    """AI searches for matches among unmatched items."""
    if not api_cfg.api_key:
        logger.warning("No API key - skipping AI search")
        if trace and trace.enabled:
            _trace_skip_all_search(results, trace, "no_api_key")
        return results
    unmatched = _get_unmatched(results)
    if len(unmatched) == 0:
        logger.info("No unmatched items to search")
        return results
    original_unmatched = len(unmatched)
    if cfg.ai_search_limit is not None and len(unmatched) > cfg.ai_search_limit:
        skipped = unmatched.iloc[cfg.ai_search_limit:]
        unmatched = unmatched.iloc[:cfg.ai_search_limit]
        if trace and trace.enabled:
            for idx, row in skipped.iterrows():
                parsed = parse_drug(row["drug_name"])
                trace.log_ai_search_not_eligible(
                    row["code"], row["drug_name"],
                    parsed.normalized, parsed.brand,
                    f"ai_search_limit={cfg.ai_search_limit}",
                    row_index=idx,
                )
    logger.info(
        f"Phase 3: AI searching for matches "
        f"among {len(unmatched)} unmatched items"
        + (
            f" (limited from {original_unmatched})"
            if len(unmatched) != original_unmatched else ""
        ),
    )
    async with AIVerifier(
        api_cfg, max_concurrent=cfg.ai_max_concurrent,
    ) as verifier:
        found = await _search_batch(
            verifier, results, index, unmatched, cfg, trace,
        )
        logger.info(f"  AI Search found {found} new matches")
    return results


__all__ = [
    "run_ai_search",
]
