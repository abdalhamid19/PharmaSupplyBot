"""Batch verification logic for AI verification."""

from __future__ import annotations

import logging

from .normalizer import parse_drug
from .verifier import AIVerifier
from .ai_verify_helpers import _trace_api_attempts, _trace_parse_failure

logger = logging.getLogger("pharmasupplybot.matching")


async def _batch_verify(verifier, items, cfg):
    all_results = []
    batch_size = cfg.ai_batch_size
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results = await verifier.verify_batch(batch)
        all_results.extend(results)
        done = min(i + batch_size, len(items))
        logger.info(f"  Verified {done}/{len(items)}")
    return all_results


async def _apply_verification(
    verifier, results, index, all_results, cfg, trace,
):
    from .ai_verify import _handle_rejected
    rejected = 0
    corrected = 0
    for vr in all_results:
        idx = vr.get("row_idx")
        if idx is None:
            continue
        drug_name = results.at[idx, "drug_name"]
        parsed = parse_drug(drug_name)
        _trace_api_attempts(trace, results, idx, parsed, vr)
        if not vr["is_correct"]:
            c, r = await _handle_rejected(
                verifier, results, index, idx, cfg, trace, vr,
            )
            corrected += c
            rejected += r
        else:
            results.at[idx, "verified"] = "ai_confirmed"
            results.at[idx, "match_method"] = "ai_verified"
            results.at[idx, "ai_confidence"] = round(vr.get("confidence", 0), 2)
            if trace and trace.enabled:
                ai_reason = vr.get("reason", "")
                if vr.get("api_failed"):
                    ai_reason = f"API unavailable ({ai_reason}), kept algo match"
                trace.log_ai_verify_result(
                    results.at[idx, "code"], drug_name,
                    parsed.normalized, parsed.brand,
                    True, "ai_confirmed",
                    "AI confirmed the algorithmic match",
                    results.at[idx, "matched_product_name_en"],
                    vr.get("confidence"), ai_reason,
                    "",
                    model_used=vr.get("model_used", ""),
                    api_failures=verifier.get_fallback_log(),
                    row_index=idx,
                    parse_failed=vr.get("parse_failed", False),
                )
                _trace_parse_failure(trace, results, idx, parsed, vr)
    return rejected, corrected
