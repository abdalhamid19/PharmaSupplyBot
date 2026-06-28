"""Risk-policy helpers for broad but reviewable Tawreed matches."""

from __future__ import annotations

from .candidate_identity import candidate_has_store_product_id
from .matching_types import CandidateMatchDiagnostic, MatchDecision, SearchMatch

AGGRESSIVE_MIN_SCORE = 12.0
AGGRESSIVE_MIN_OVERLAP = 0.45


def aggressive_review_decision(
    decision: MatchDecision, cfg: Any = None
) -> MatchDecision | None:
    """Return a flagged best candidate when safe matching found no winner."""
    if decision.best_match:
        return None
    diagnostic = _best_aggressive_diagnostic(decision.diagnostics, cfg)
    if diagnostic is None:
        return None
    return MatchDecision(
        _search_match(diagnostic),
        decision.diagnostics,
        _aggressive_reason(diagnostic),
    )


def is_aggressive_flagged_decision(decision: MatchDecision | None) -> bool:
    return bool(decision and decision.final_reason.startswith("Aggressive flagged"))


def _best_aggressive_diagnostic(diagnostics: list[CandidateMatchDiagnostic], cfg: Any = None) -> CandidateMatchDiagnostic | None:
    candidates = [d for d in diagnostics if _can_aggressively_flag(d, cfg)]
    return max(candidates, key=lambda d: d.sort_key, default=None)


def _share_brand_identity_token(query: str, candidate: dict[str, Any]) -> bool:
    from .drug_matching.normalizer import parse_drug
    from .order_ai_records import candidate_name
    import re

    req = parse_drug(query)
    off = parse_drug(candidate_name(candidate))
    if not req.brand or not off.brand:
        return False

    if _brands_share_tokens(req, off):
        return True
    return _brands_similar_fuzzy(req.brand, off.brand)


def _brands_share_tokens(req, off):
    import re
    req_tokens = set(re.findall(r"[A-Z0-9]+", req.brand.upper()))
    off_tokens = set(re.findall(r"[A-Z0-9]+", off.brand.upper()))
    for var in req.brand_variants:
        req_tokens.update(re.findall(r"[A-Z0-9]+", var.upper()))
    for var in off.brand_variants:
        off_tokens.update(re.findall(r"[A-Z0-9]+", var.upper()))
    return bool(req_tokens & off_tokens)


def _brands_similar_fuzzy(req_brand, off_brand):
    import re
    from rapidfuzz import fuzz
    req_clean = re.sub(r"[^A-Z0-9]", "", req_brand.upper())
    off_clean = re.sub(r"[^A-Z0-9]", "", off_brand.upper())
    if req_clean and off_clean:
        if req_clean in off_clean or off_clean in req_clean:
            return True
        if fuzz.ratio(req_clean, off_clean) >= 80:
            return True
    return False


def _can_aggressively_flag(diagnostic: CandidateMatchDiagnostic, cfg: Any = None) -> bool:
    if not candidate_has_store_product_id(diagnostic.candidate):
        return False
    if diagnostic.score < AGGRESSIVE_MIN_SCORE:
        return False
    if diagnostic.breakdown.overlap_score < AGGRESSIVE_MIN_OVERLAP:
        return False
    require_token = True if cfg is None else getattr(cfg, "require_identity_token_for_flag", True)
    if require_token:
        if not _share_brand_identity_token(diagnostic.query, diagnostic.candidate):
            return False
    return True


def _aggressive_reason(diagnostic: CandidateMatchDiagnostic) -> str:
    reason = diagnostic.rejection_reason or diagnostic.accepted_reason
    return f"Aggressive flagged match requires manual review: score={diagnostic.score:.3f}; reason={reason}"


def _search_match(diagnostic: CandidateMatchDiagnostic) -> SearchMatch:
    return SearchMatch(diagnostic.query, diagnostic.row_index, diagnostic.score, diagnostic.candidate)
