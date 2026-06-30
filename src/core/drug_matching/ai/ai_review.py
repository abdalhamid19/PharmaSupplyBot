"""AI review logic for cross-verifying low-confidence AI decisions."""

from __future__ import annotations

import logging

import pandas as pd

from ..config import MatchingConfig, APIConfig
from ..indexing.indexer import DrugIndex
from ..normalization.normalizer import parse_drug
from ..pricing import price_context
from ..verification.verifier import AIVerifier
from .ai_review_selection import _select_for_review, _build_review_items
from .ai_review_execution import _batch_review, _apply_review_results

logger = logging.getLogger("pharmasupplybot.matching")


def _trace_skip_all_review(results, trace, reason):
    """Log AI review skip for all AI-verified drugs."""
    ai_verified = results[
        results["verified"].isin(["ai_confirmed", "ai_corrected", "ai_found", "ai_rejected"])
    ]
    for idx, row in ai_verified.iterrows():
        parsed = parse_drug(row["drug_name"])
        trace.log_ai_skip(
            row["code"], row["drug_name"],
            parsed.normalized, parsed.brand,
            "review", reason, row_index=idx,
        )


async def run_ai_review(
    results: pd.DataFrame,
    index: DrugIndex,
    cfg: MatchingConfig,
    api_cfg: APIConfig,
    trace=None,
) -> pd.DataFrame:
    """AI review: second model cross-verifies low-confidence AI decisions."""
    if not api_cfg.api_key or not api_cfg.review_model:
        logger.info("No review model configured - skipping AI review")
        if trace and trace.enabled:
            _trace_skip_all_review(results, trace, "no_review_model")
        return results
    if api_cfg.review_model == "rotation" and not api_cfg.review_attempt_plan:
        logger.info("No strong review model available - skipping AI review")
        if trace and trace.enabled:
            _trace_skip_all_review(results, trace, "no_strong_review_model")
        return results
    to_review = _select_for_review(results, cfg)
    if len(to_review) == 0:
        logger.info("No low-confidence AI decisions to review")
        return results
    logger.info(
        f"Phase 4: Reviewing {len(to_review)} low-confidence AI decisions "
        f"with second model (threshold={cfg.ai_review_threshold})",
    )
    if trace and trace.enabled:
        for idx, row in to_review.iterrows():
            parsed = parse_drug(row["drug_name"])
            conf = pd.to_numeric(row.get("ai_confidence", 0), errors="coerce")
            is_api_failed = (conf == 0.0)
            trace.log_ai_review_sent(
                row["code"], row["drug_name"],
                parsed.normalized, parsed.brand,
                row["verified"], row["ai_confidence"],
                row["matched_product_name_en"],
                first_model=api_cfg.model,
                review_model=api_cfg.review_model,
                api_failed=is_api_failed,
                price_context=price_context(
                    row.get("_drug_price", ""),
                    row.get("_matched_price", ""),
                ),
                row_index=idx,
            )
    items = _build_review_items(to_review)
    async with AIVerifier(
        api_cfg, max_concurrent=cfg.ai_max_concurrent,
    ) as verifier:
        all_results = await _batch_review(verifier, items, cfg)
        overridden = await _apply_review_results(
            verifier, results, index, all_results, cfg, trace,
        )
        logger.info(
            f"  Review Results: "
            f"confirmed={len(all_results)-overridden}, "
            f"overridden={overridden}",
        )
    return results
