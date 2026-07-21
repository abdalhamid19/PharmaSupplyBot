"""Main AI verification entry point."""

from __future__ import annotations

import logging
import pandas as pd

from ..config import MatchingConfig, APIConfig
from ..normalization.normalizer import parse_drug
from ..indexing.indexer import DrugIndex
from ..pricing import price_context
from ..verification.verifier import AIVerifier
from .ai_verify_helpers import _trace_skip_all_verify
from .ai_verify_selection import _select_for_verification, _build_verify_items
from .ai_verify_batch import _batch_verify, _apply_verification

logger = logging.getLogger(__name__)


async def run_ai_verification(
    results: pd.DataFrame,
    index: DrugIndex,
    cfg: MatchingConfig,
    api_cfg: APIConfig,
    trace=None,
) -> pd.DataFrame:
    """AI verification of matches below threshold."""
    if not api_cfg.api_key:
        logger.warning("No API key - skipping AI verification")
        if trace and trace.enabled:
            _trace_skip_all_verify(results, trace, "no_api_key")
        return results
    to_verify = _select_for_verification(results, cfg)
    if len(to_verify) == 0:
        logger.info("No matches below AI verification threshold")
        return results
    logger.info(
        f"Phase 2: Verifying {len(to_verify)} matches "
        f"with AI (threshold={cfg.ai_verify_threshold})",
    )
    _log_verification_trace(to_verify, cfg, api_cfg, trace)
    items = _build_verify_items(to_verify)
    results = await _execute_verification(
        results, index, items, cfg, api_cfg, trace
    )
    return results


def _log_verification_trace(to_verify, cfg, api_cfg, trace):
    """Log trace information for verification."""
    if trace and trace.enabled:
        for idx, row in to_verify.iterrows():
            parsed = parse_drug(row["drug_name"])
            score = pd.to_numeric(row["match_score"], errors="coerce")
            trace.log_ai_verify_sent(
                row["code"], row["drug_name"],
                parsed.normalized, parsed.brand,
                score, cfg.ai_verify_threshold,
                row["matched_product_name_en"],
                parsed.brand, row["match_method"],
                ai_model=api_cfg.model,
                price_context=price_context(
                    row.get("_drug_price", ""),
                    row.get("_matched_price", ""),
                ),
                row_index=idx,
            )


async def _execute_verification(results, index, items, cfg, api_cfg, trace):
    """Execute the verification process and log results."""
    async with AIVerifier(
        api_cfg, max_concurrent=cfg.ai_max_concurrent,
    ) as verifier:
        all_results = await _batch_verify(verifier, items, cfg)
        rejected, corrected = await _apply_verification(
            verifier, results, index, all_results, cfg, trace,
        )
        logger.info(
            f"  AI Results: "
            f"confirmed={len(all_results)-rejected-corrected}, "
            f"corrected={corrected}, rejected={rejected}",
        )
    return results


# Export for backward compatibility
__all__ = [
    "run_ai_verification",
    "_select_for_verification",
    "_build_verify_items",
]
