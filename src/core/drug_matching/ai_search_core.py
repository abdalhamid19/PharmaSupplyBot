"""Core search execution functions for AI search."""

import asyncio
import logging

import pandas as pd

from .config import MatchingConfig
from .normalizer import parse_drug
from .indexer import DrugIndex
from .pricing import price_context
from .verifier import AIVerifier
from .ai_search_candidates import (
    _search_candidates,
    _eligible_search_candidates,
    _search_acceptance_threshold,
    _apply_search_result,
)
from .ai_search_trace import (
    _trace_api_attempts,
    _trace_parse_failure,
    _search_error_code,
    _trace_search_exception,
)

logger = logging.getLogger("pharmasupplybot.matching")


async def _try_search_one(verifier, results, index, row, cfg, trace):
    """Try to search for one unmatched item."""
    drug_name = row["drug_name"]
    parsed = parse_drug(drug_name)
    norm = parsed.normalized
    code = str(row.get("code", ""))
    if not norm or len(norm) < 3:
        if trace and trace.enabled:
            trace.log_ai_skip(
                code, drug_name, norm, parsed.brand,
                "search", "norm too short for AI search",
                row_index=row.name,
            )
        return 0
    price = row.get("_drug_price", "")
    candidates = _search_candidates(parsed, norm, index, cfg, price)
    if not candidates:
        if trace and trace.enabled:
            trace.log_ai_skip(
                code, drug_name, norm, parsed.brand,
                "search", "no valid candidates found",
                row_index=row.name,
            )
        return 0
    candidates = _eligible_search_candidates(parsed, candidates, index, cfg)
    if not candidates:
        if trace and trace.enabled:
            trace.log_ai_search_not_eligible(
                code, drug_name, norm, parsed.brand,
                (
                    "ai_search_skipped_not_eligible: "
                    f"no candidate >= {cfg.ai_search_min_candidate_score}"
                    " with safe components"
                ),
                row_index=row.name,
            )
        return 0
    if trace and trace.enabled:
        cand_names = [
            c[0]["product_name_en"] for c in candidates
        ]
        trace.log_ai_search_sent(
            code, drug_name, norm, parsed.brand,
            len(candidates), cand_names,
            ai_model=verifier._cfg.model,
            price_context=price_context(price, None),
            row_index=row.name,
        )
    ai_result = await verifier.find_better_match(
        drug_name, candidates, inventory_price=price,
    )
    if ai_result:
        _trace_api_attempts(trace, results, row.name, parsed, ai_result)
        _trace_parse_failure(trace, results, row.name, parsed, ai_result)
        confidence = ai_result.get("confidence", 0) if ai_result else 0
        accept_threshold, acceptance_reason = _search_acceptance_threshold(
            ai_result, candidates, parsed, index, cfg,
        )
        if (
            ai_result and ai_result.get("record")
            and confidence >= accept_threshold
            and acceptance_reason != "unsafe_component_mismatch"
        ):
            match_name = ai_result["record"]["product_name_en"]
            ai_result["_component_reason"] = acceptance_reason
            _apply_search_result(results, row.name, ai_result)
            if trace and trace.enabled:
                trace.log_ai_search_result(
                    code, drug_name, norm, parsed.brand,
                    True, match_name, confidence,
                    model_used=ai_result.get("model_used", ""),
                    api_failures=verifier.get_fallback_log(),
                    accept_threshold=accept_threshold,
                    row_index=row.name,
                    parse_failed=ai_result.get("parse_failed", False),
                )
            return 1
    if trace and trace.enabled:
        error_code = _search_error_code(
            ai_result, confidence, 0.75,
        )
        if acceptance_reason == "unsafe_component_mismatch":
            error_code = acceptance_reason
        trace.log_ai_search_result(
            code, drug_name, norm, parsed.brand,
            False, None, confidence,
            model_used=ai_result.get("model_used", "") if ai_result else "",
            api_failures=verifier.get_fallback_log(),
            accept_threshold=accept_threshold,
            row_index=row.name,
            error_code=error_code,
            parse_failed=ai_result.get("parse_failed", False) if ai_result else False,
        )
    return 0


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


__all__ = [
    "_try_search_one",
    "_search_batch",
]
