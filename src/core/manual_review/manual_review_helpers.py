"""Helper functions for manual review runtime."""

import logging
import time

from .manual_review_store import ManualReviewDecision, ManualReviewStore
from ..utils.excel import Item
from ..identity.manufacturer_identity import manufacturer_conflict

logger = logging.getLogger(__name__)


def _lookup_with_retry(item: Item, max_attempts: int = 3) -> ManualReviewDecision | None:
    """Lookup decision with retry logic."""
    for attempt in range(max_attempts):
        try:
            # Use default path resolved at call time so tests can patch DEFAULT_MANUAL_REVIEW_DB
            result = ManualReviewStore().lookup(item.code, item.name)
            if attempt > 0:
                logger.info(f"Manual review lookup succeeded on attempt {attempt + 1} for {item.code}/{item.name}")
            return result
        except Exception as e:
            if attempt < max_attempts - 1:
                _log_retry_warning(item, attempt, e)
                time.sleep(0.05 * (attempt + 1))
            else:
                _log_retry_failure(item, max_attempts, e)
                return None


def _log_retry_warning(item, attempt, e):
    """Log retry warning."""
    logger.warning(
        f"Manual review lookup attempt {attempt + 1} failed for {item.code}/{item.name}: "
        f"{type(e).__name__}: {e}, retrying..."
    )


def _log_retry_failure(item, max_attempts, e):
    """Log retry failure."""
    logger.error(
        f"Manual review lookup failed after {max_attempts} attempts for {item.code}/{item.name}: "
        f"{type(e).__name__}: {e}"
    )


def _blocks_candidate(decision: ManualReviewDecision | None) -> bool:
    """Check if decision blocks candidate."""
    return bool(
        decision
        and decision.manual_decision == "not_matching"
        and decision.correct_store_product_id
    )


def _preferred_queries(decision: ManualReviewDecision | None) -> list[str]:
    """Extract preferred queries from decision."""
    if not decision:
        return []
    if decision.correct_query:
        return [decision.correct_query]
    return [decision.correct_product_name, getattr(decision, "correct_product_name_ar", "")]


def _find_manual_review_match(
    results, target_id, target_en, target_ar, item=None, decision=None
):
    """
    Find match by ID or name.
    
    # البحث عن تطابق بالمعرف أو الاسم
    """
    if target_id:
        id_match = _manual_review_id_match(results, target_id, item, decision)
        if id_match is not None:
            return id_match
    return _manual_review_name_match(results, target_en, target_ar, item, decision)


def _manual_review_id_match(
    results: list[tuple[str, list[dict]]],
    target_id: str,
    item: Item | None = None,
    decision: ManualReviewDecision | None = None,
):
    """
    Force a match when a candidate exposes the saved orderable store id.
    
    # فرض تطابق عندما يعرض المرشح معرف المتجر المحفوظ
    """
    from ..matching.candidate_identity import candidate_store_product_id
    from ..matching_types import SearchMatch, MatchDecision

    for query, candidates in results:
        for index, candidate in enumerate(candidates):
            if candidate_store_product_id(candidate) == target_id:
                # Skip validation for ID match to preserve backward compatibility
                # التخطي من التحقق لمطابقة المعرف للحفاظ على التوافق مع الإصدارات السابقة
                match = SearchMatch(query, index, 999.0, candidate)
                return MatchDecision(match, [], "Approved by saved manual review (ID match).")
    return None


def _manual_review_name_match(
    results: list[tuple[str, list[dict]]],
    target_en: str,
    target_ar: str,
    item: Item | None = None,
    decision: ManualReviewDecision | None = None,
):
    """
    Force a match when an orderable candidate exactly matches the saved name.
    
    # فرض تطابق عندما يطابق المرشح القابل للطلب الاسم المحفوظ تماماً
    """
    if not target_en and not target_ar:
        return None
    
    for query, candidates in results:
        match = _find_name_match_in_candidates(
            candidates, target_en, target_ar, query, item, decision
        )
        if match:
            return match
    return None


def _find_name_match_in_candidates(
    candidates, target_en, target_ar, query, item=None, decision=None
):
    """
    Find name match within candidates list.
    
    # البحث عن تطابق الاسم داخل قائمة المرشحين
    """
    from ..ordering.order_ai_matching import candidate_name, candidate_ar
    from ..matching.candidate_identity import candidate_store_product_id
    from ..matching_types import SearchMatch, MatchDecision
    
    for index, candidate in enumerate(candidates):
        c_en = candidate_name(candidate).lower()
        c_ar = candidate_ar(candidate).lower()
        if not ((target_en and c_en == target_en) or (target_ar and c_ar == target_ar)):
            continue
        # Orderable rows force an immediate accepted match. Non-orderable rows
        # (empty storeProductId) still count as a recognized approved product so
        # downstream status can become not-orderable instead of no-results.
        match = SearchMatch(query, index, 999.0, candidate)
        if candidate_store_product_id(candidate):
            return MatchDecision(
                match, [], "Approved by saved manual review (Name match)."
            )
        return MatchDecision(
            match,
            [],
            "Approved by saved manual review (Name match, not orderable).",
        )
    return None


def _validate_manual_review_match(
    item: Item,
    candidate: dict,
    decision: ManualReviewDecision,
) -> tuple[bool, str]:
    """
    Validate a manual review match before accepting it with score 999.
    
    # التحقق من صحة تطابق المراجعة اليدوية قبل قبوله بدرجة 999
    
    Checks:
    - Does the saved product still match the current item?
    - Is there a clear manufacturer/brand conflict?
    - Has the saved name changed to a different product?
    
    Returns:
        (is_valid, reason) tuple
    """
    # Check product ID match - التحقق من تطابق معرف المنتج
    id_valid, id_reason = _validate_product_id_match(candidate, decision)
    if not id_valid:
        return False, id_reason
    
    # Check manufacturer conflict - التحقق من تضارب الشركة المصنعة
    mfg_valid, mfg_reason = _validate_manufacturer_match(item, candidate)
    if not mfg_valid:
        return False, mfg_reason
    
    # Check name consistency - التحقق من اتساق الاسم
    name_valid, name_reason = _validate_name_consistency(candidate, decision)
    if not name_valid:
        return False, name_reason
    
    return True, "Validation passed"


def _validate_product_id_match(
    candidate: dict, decision: ManualReviewDecision
) -> tuple[bool, str]:
    """
    Check if product ID still matches the saved decision.
    
    # التحقق من أن معرف المنتج لا يزال مطابقاً للقرار المحفوظ
    """
    saved_id = decision.correct_store_product_id
    if not saved_id:
        return True, "No saved ID to validate"
    
    from ..matching.candidate_identity import candidate_store_product_id
    current_id = candidate_store_product_id(candidate)
    if current_id and current_id != saved_id:
        return False, f"Product ID mismatch: saved {saved_id}, current {current_id}"
    
    return True, "ID matches"


def _validate_manufacturer_match(
    item: Item, candidate: dict
) -> tuple[bool, str]:
    """
    Check for manufacturer/brand conflict between item and candidate.
    
    # التحقق من تضارب الشركة المصنعة/العلامة التجارية بين العنصر والمرشح
    """
    item_manufacturer = _extract_item_manufacturer(item)
    candidate_manufacturer = _extract_candidate_manufacturer(candidate)
    
    if item_manufacturer and candidate_manufacturer:
        if manufacturer_conflict(item_manufacturer, candidate_manufacturer):
            return False, (
                f"Manufacturer conflict: item '{item_manufacturer}' vs "
                f"candidate '{candidate_manufacturer}'"
            )
    
    return True, "No manufacturer conflict"


def _validate_name_consistency(
    candidate: dict, decision: ManualReviewDecision
) -> tuple[bool, str]:
    """
    Check if saved name changed significantly to a different product.
    
    # التحقق من أن الاسم المحفوظ لم يتغير بشكل كبير لمنتج مختلف
    """
    saved_name = decision.correct_product_name or ""
    if not saved_name:
        return True, "No saved name to validate"
    
    from ..ordering.order_ai_matching import candidate_name
    current_name = candidate_name(candidate).lower()
    
    if saved_name.lower() != current_name:
        if _is_major_name_change(saved_name, current_name):
            return False, (
                f"Name changed significantly: saved '{saved_name}' vs "
                f"current '{current_name}'"
            )
    
    return True, "Name is consistent"


def _extract_item_manufacturer(item: Item) -> str | None:
    """
    Extract manufacturer from item name.
    
    # استخراج الشركة المصنعة من اسم المنتج
    """
    from ..identity.manufacturer_identity import extract_manufacturer_from_name
    return extract_manufacturer_from_name(item.name)


def _extract_candidate_manufacturer(candidate: dict) -> str | None:
    """
    Extract manufacturer from candidate data.
    
    # استخراج الشركة المصنعة من بيانات المرشح
    """
    from ..identity.manufacturer_identity import extract_manufacturer_from_candidate
    from ..ordering.order_ai_matching import candidate_name
    
    company_name = candidate.get("companyName") or candidate.get("company_name")
    supplier_name = candidate.get("supplierName") or candidate.get("supplier_name")
    cand_name = candidate_name(candidate)
    
    return extract_manufacturer_from_candidate(cand_name, company_name, supplier_name)


def _is_major_name_change(saved_name: str, current_name: str) -> bool:
    """
    Check if name change is major (different product).
    
    # التحقق من أن تغير الاسم كبير (منتج مختلف)
    
    Simple heuristic: if less than 50% token overlap, it's a major change.
    """
    from ..matching.product_matching_helpers import normalize_text
    
    saved_tokens = set(normalize_text(saved_name).split())
    current_tokens = set(normalize_text(current_name).split())
    
    if not saved_tokens or not current_tokens:
        return False
    
    overlap = len(saved_tokens & current_tokens)
    max_len = max(len(saved_tokens), len(current_tokens))
    ratio = overlap / max_len if max_len > 0 else 0
    
    return ratio < 0.5


def should_skip_auto_save(
    item: Item,
    candidate: dict,
    rejection_reason: str | None = None,
) -> tuple[bool, str]:
    """
    Check if auto-save should be skipped due to conflicts or issues.
    
    # التحقق من أن الحفظ التلقائي يجب تخطيه بسبب التضاربات أو المشاكل
    
    This helper is intended for use in _auto_save_verified_match to prevent
    saving matches that have conflicts or were rejected due to conflicts.
    
    Returns:
        (should_skip, reason) tuple
    """
    # Skip if there's a conflict-related rejection reason
    # تخطي إذا كان هناك سبب رفض متعلق بالتضارب
    if rejection_reason:
        rejection_lower = rejection_reason.lower()
        conflict_keywords = ["conflict", "manufacturer", "brand", "semantic"]
        if any(keyword in rejection_lower for keyword in conflict_keywords):
            return True, f"Conflict-related rejection: {rejection_reason}"
    
    # Check for manufacturer conflict - التحقق من تضارب الشركة المصنعة
    item_manufacturer = _extract_item_manufacturer(item)
    candidate_manufacturer = _extract_candidate_manufacturer(candidate)
    
    if item_manufacturer and candidate_manufacturer:
        if manufacturer_conflict(item_manufacturer, candidate_manufacturer):
            return True, (
                f"Manufacturer conflict detected for auto-save: "
                f"item '{item_manufacturer}' vs candidate '{candidate_manufacturer}'"
            )
    
    return False, "No conflicts detected"


__all__ = [
    "_lookup_with_retry",
    "_log_retry_warning",
    "_log_retry_failure",
    "_blocks_candidate",
    "_preferred_queries",
    "_find_manual_review_match",
    "_manual_review_id_match",
    "_manual_review_name_match",
    "_find_name_match_in_candidates",
    "_validate_manual_review_match",
    "_validate_product_id_match",
    "_validate_manufacturer_match",
    "_validate_name_consistency",
    "_extract_item_manufacturer",
    "_extract_candidate_manufacturer",
    "_is_major_name_change",
    "should_skip_auto_save",
]
