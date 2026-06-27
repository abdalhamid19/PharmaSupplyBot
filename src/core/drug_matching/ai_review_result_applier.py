"""Result application logic for AI review - handles different review scenarios."""

import pandas as pd

from .config import MatchingConfig
from .indexer import DrugIndex
from .normalizer import parse_drug, components_match
from .verifier import AIVerifier
from .ai_verify import (
    _trace_api_attempts, _trace_parse_failure, _clear_match,
    _apply_correction, _internal_value
)
from .ai_review_component import (
    _component_review_required, _safe_reviewed_component_mismatch,
    _reject_reviewed_component_mismatch
)
from .ai_review_scenario_handlers import (
    handle_api_failed, handle_disagreement, handle_agreement
)

_AI_REVIEW_OVERRIDE_CONFIDENCE = 0.75


class ReviewResultApplier:
    """Applies AI review results to the results dataframe."""

    def __init__(self, verifier, results, index, cfg, trace):
        self._verifier = verifier
        self._results = results
        self._index = index
        self._cfg = cfg
        self._trace = trace

    async def apply_results(self, all_results):
        """Apply review results: if second model disagrees, re-evaluate.
        For api_failed items, is_correct is a direct fresh decision."""
        overridden = 0
        for rr in all_results:
            idx = rr.get("row_idx")
            if idx is None:
                continue
            drug_name = self._results.at[idx, "drug_name"]
            parsed = parse_drug(drug_name)
            first_decision = self._results.at[idx, "verified"]
            review_confidence = rr.get("confidence", 0)
            review_confidence = pd.to_numeric(review_confidence, errors="coerce")
            if pd.isna(review_confidence):
                review_confidence = 0.0
            review_reason = rr.get("reason", "")
            is_correct = rr.get("is_correct", True)
            is_api_failed = rr.get("api_failed", False)
            component_reason = _component_review_required(self._results, idx)
            _trace_api_attempts(self._trace, self._results, idx, parsed, rr)
            _trace_parse_failure(self._trace, self._results, idx, parsed, rr)

            if is_api_failed:
                overridden += handle_api_failed(
                    self._verifier, self._results, self._trace, idx, drug_name,
                    parsed, is_correct, review_confidence, review_reason, rr
                )
            elif (
                component_reason
                and first_decision in {"ai_confirmed", "ai_corrected", "ai_found"}
                and (
                    not is_correct
                    or review_confidence < max(
                        _AI_REVIEW_OVERRIDE_CONFIDENCE,
                        self._cfg.ai_search_review_accept_confidence,
                    )
                    or not _safe_reviewed_component_mismatch(
                        self._results, idx, self._cfg, component_reason,
                    )
                )
            ):
                overridden += 1
                _reject_reviewed_component_mismatch(
                    self._verifier, self._results, idx, parsed, review_confidence,
                    review_reason, self._trace, rr,
                )
            elif is_correct:
                # Second model agrees with first AI
                handle_agreement(
                    self._verifier, self._results, self._trace, idx, drug_name,
                    parsed, first_decision, review_confidence, review_reason, rr
                )
            else:
                # Second model disagrees with first AI
                overridden += await handle_disagreement(
                    self._verifier, self._results, self._index, self._cfg,
                    self._trace, idx, drug_name, parsed, first_decision,
                    review_confidence, review_reason, rr
                )
        return overridden
