"""Structured rows for order item summary artifacts."""

from __future__ import annotations

from ..identity.manufacturer_identity import (
    extract_manufacturer_from_candidate,
    extract_manufacturer_from_name,
    manufacturer_conflict,
)

# Constants
REVIEWABLE_STATUSES = {
    "no-results", "matched-but-unavailable", "not-orderable", "manual-review-required",
    "manufacturer-mismatch",
}
SUMMARY_TIMING_KEYS = (
    "api_context_init_seconds",
    "api_search_seconds",
    "dom_wait_seconds",
    "dialog_close_seconds",
    "manual_review_lookup_seconds",
    "match_decision_seconds",
    "add_to_cart_seconds",
    "artifact_write_seconds",
    "summary_build_seconds",
)

# Helper functions
def _extract_diagnostic_and_match(status, match, decision, blocked_candidate, outcome):
    """
    Extract best diagnostic and match source for not-orderable items.
    استخراج أفضل تشخيص ومصدر مطابق للعناصر غير القابلة للطلب.
    """
    best_diagnostic = None
    match_source = match.data if match else {}
    
    if status in ("not-orderable", "matched-but-unavailable") and not match:
        best_diagnostic, match_source, blocked_candidate = _handle_not_orderable(
            decision, best_diagnostic, match_source, blocked_candidate
        )
    
    match_source = _handle_missing_product_id(match, match_source, blocked_candidate, outcome)
    
    return best_diagnostic, match_source, blocked_candidate


def _handle_not_orderable(decision, best_diagnostic, match_source, blocked_candidate):
    """
    Handle not-orderable status by extracting diagnostics.
    معالجة حالة غير قابلة للطلب عن طريق استخراج التشخيصات.
    """
    best_diagnostic = _find_best_diagnostic(decision)
    if best_diagnostic and getattr(best_diagnostic, "candidate", None):
        if not blocked_candidate:
            blocked_candidate = best_diagnostic.candidate
    match_source, best_diagnostic = _resolve_match_source(
        decision, best_diagnostic, match_source
    )
    return best_diagnostic, match_source, blocked_candidate


def _handle_missing_product_id(match, match_source, blocked_candidate, outcome):
    """
    Handle missing store product ID outcome.
    معالجة نتيجة معرف المنتج المفقود في المتجر.
    """
    if not match and not match_source:
        from .order_blocked_candidate import missing_store_product_id_outcome
        if missing_store_product_id_outcome(outcome):
            match_source = blocked_candidate
    return match_source


def _find_best_diagnostic(decision):
    """
    Find the best diagnostic from decision.
    العثور على أفضل تشخيص من القرار.
    """
    if not decision or not getattr(decision, "diagnostics", None):
        return None
    return max(decision.diagnostics, key=lambda d: d.score, default=None)


def _resolve_match_source(decision, best_diagnostic, match_source):
    """
    Find match_source for orderable-missing diagnostics.
    العثور على مصدر المطابقة للتشخيصات المفقودة القابلة للطلب.
    """
    if not decision or not getattr(decision, "diagnostics", None):
        return match_source, best_diagnostic
    
    orderable_missing_diag = _find_orderable_missing_diag(decision)
    if orderable_missing_diag:
        match_source = orderable_missing_diag.candidate
        best_diagnostic = orderable_missing_diag
    
    return match_source, best_diagnostic


def _find_orderable_missing_diag(decision):
    """
    Find diagnostic for orderable-missing store product ID.
    العثور على تشخيص لمعرف المنتج المفقود القابل للطلب.
    """
    return next(
        (
            d for d in decision.diagnostics
            if getattr(d, "rejection_reason", "") ==
            "Candidate missing orderable storeProductId"
        ),
        None
    )


def _extract_query_and_score(match, blocked_candidate, outcome, best_diagnostic):
    """
    Extract matched query and deterministic score.
    استخراج الاستعلام المطابق والدرجة الحتمية.
    """
    matched_query = match.query if match else blocked_candidate_query(outcome)
    if not matched_query and best_diagnostic:
        matched_query = best_diagnostic.query
        
    det_score = round(match.score, 6) if match else ""
    if not det_score and best_diagnostic:
        det_score = round(best_diagnostic.score, 6)
    
    return matched_query, det_score


def _basic_item_fields(item, summary, status, matched_query, det_score):
    """
    Extract basic item fields.
    استخراج الحقول الأساسية للعنصر.
    """
    return {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": status,
        "reason": summary.reason,
        "ordered_total_qty": getattr(summary, "ordered_total_qty", ""),
        "matched_query": matched_query,
        "deterministic_score": det_score,
    }


def _timing_fields(summary):
    """
    Extract timing fields from summary.
    استخراج حقول التوقيت من الملخص.
    """
    return {
        "elapsed_seconds": round(float(getattr(summary, "elapsed_seconds", 0.0)), 3),
        "match_elapsed_seconds": round(
            float(getattr(summary, "match_elapsed_seconds", 0.0)), 3
        ),
        **_summary_timing_fields(summary),
    }


def _summary_timing_fields(summary) -> dict[str, float]:
    """
    Extract summary timing fields.
    استخراج حقول توقيت الملخص.
    """
    timings = getattr(summary, "timing_seconds", None) or {}
    return {
        key: round(float(timings.get(key, 0.0)), 3)
        for key in SUMMARY_TIMING_KEYS
    }


def _manufacturer_diagnostic_fields(
    matched_query: str, match_source: dict, decision, config=None
) -> dict[str, object]:
    """
    Extract manufacturer diagnostic fields for artifacts.
    استخراج حقول تشخيص المصنع للأرتيفاكت.
    """
    query_company = _extract_query_manufacturer(matched_query)
    candidate_company = _extract_candidate_manufacturer(match_source)
    check_decision = _compute_manufacturer_decision(
        query_company, candidate_company, config
    )
    
    return {
        "query_manufacturer": query_company or "",
        "candidate_manufacturer": candidate_company or "",
        "manufacturer_check_decision": check_decision,
    }


def _decision_clarity_fields(item, decision, outcome) -> dict[str, object]:
    """
    Extract fields that clarify why decisions were made.
    استخراج الحقول التي توضح سبب اتخاذ القرارات.

    Includes saved manual review decisions and higher-scoring rejected candidates.
    تتضمن قرارات المراجعة اليدوية المحفوظة والمرشحين المرفوضين الأعلى درجة.
    """
    fields = _init_decision_clarity_fields()
    fields.update(_extract_saved_manual_decision(item))
    fields.update(_extract_rejected_candidate_info(decision))
    return fields


def _init_decision_clarity_fields() -> dict[str, object]:
    """
    Initialize decision clarity fields with empty values.
    تهيئة حقول وضوح القرار بقيم فارغة.
    """
    return {
        "saved_manual_review_decision": "",
        "saved_manual_review_safety_decision": "",
        "higher_scoring_rejected_candidate": "",
        "higher_scoring_rejection_reason": "",
    }


def _extract_saved_manual_decision(item) -> dict[str, object]:
    """
    Extract saved manual review decision from item.
    استخراج قرار المراجعة اليدوية المحفوظ من العنصر.
    """
    from ..manual_review.manual_review_runtime import saved_manual_review_decision
    
    saved_decision = saved_manual_review_decision(item)
    if not saved_decision:
        return {}
    
    return {
        "saved_manual_review_decision": saved_decision.manual_decision or "",
        "saved_manual_review_safety_decision": (
            getattr(saved_decision, "safety_decision", "") or ""
        ),
    }


def _extract_rejected_candidate_info(decision) -> dict[str, object]:
    """
    Extract higher-scoring rejected candidate information.
    استخراج معلومات المرشح المرفوض الأعلى درجة.
    """
    if not decision or not hasattr(decision, "diagnostics"):
        return {}
    
    rejected = _find_higher_scoring_rejected(decision)
    if not rejected:
        return {}
    
    return {
        "higher_scoring_rejected_candidate": (
            getattr(rejected.candidate, "productNameEn", "") or ""
        ),
        "higher_scoring_rejection_reason": (
            getattr(rejected, "rejection_reason", "") or ""
        ),
    }


def _find_higher_scoring_rejected(decision) -> object | None:
    """
    Find the highest-scoring rejected candidate from diagnostics.
    العثور على المرشح المرفوض الأعلى درجة من التشخيصات.

    Returns the diagnostic with highest score that was rejected.
    يُرجع التشخيص بأعلى درجة تم رفضه.
    """
    if not decision or not hasattr(decision, "diagnostics"):
        return None
    
    rejected = [
        d for d in decision.diagnostics
        if getattr(d, "rejection_reason", None)
    ]
    
    if not rejected:
        return None
    
    return max(rejected, key=lambda d: getattr(d, "score", 0), default=None)


def _extract_query_manufacturer(matched_query: str) -> str | None:
    """
    Extract manufacturer from the matched query string.
    استخراج المصنع من سلسلة الاستعلام المطابقة.
    """
    return (extract_manufacturer_from_name(matched_query) or "").upper() if matched_query else ""


def _extract_candidate_manufacturer(match_source: dict) -> str | None:
    """
    Extract manufacturer from the candidate source.
    استخراج اسم المصنع من مصدر المرشح.

    Only claims manufacturer if companyName is not present.
    If companyName is stored, we don't claim manufacturer from productName.
    """
    if not match_source:
        return ""
    
    company_name = match_source.get("companyName")
    if company_name:
        return company_name.upper()
    
    return _extract_manufacturer_from_product(match_source)


def _extract_manufacturer_from_product(match_source: dict) -> str:
    """
    Extract manufacturer from product name and supplier.
    استخراج المصنع من اسم المنتج والمورد.
    """
    candidate_name = match_source.get("productNameEn", "")
    supplier_name = match_source.get("supplierName", "")
    
    return (extract_manufacturer_from_candidate(
        candidate_name,
        None,  # Don't pass companyName since we already checked it
        supplier_name,
    ) or "").upper()


def _compute_manufacturer_decision(
    query_company: str, candidate_company: str, config
) -> str:
    """
    Compute manufacturer check decision (match/conflict/unknown).
    حساب قرار فحص المصنع (مطابقة/تعارض/غير معروف).
    """
    if not query_company or not candidate_company:
        return "unknown"
    
    threshold = getattr(config, "manufacturer_match_threshold", 0.85) if config else 0.85
    if manufacturer_conflict(query_company, candidate_company, threshold):
        return "conflict"
    return "match"


def _manual_review_reason_code(summary_status: str, outcome) -> str:
    """
    Extract manual review reason code from outcome.
    استخراج رمز سبب المراجعة اليدوية من النتيجة.
    """
    status = getattr(outcome, "status", "") if outcome is not None else ""
    return status or summary_status


def _final_action(summary_status: str, manual_review: bool) -> str:
    """
    Determine final action based on manual review status.
    تحديد الإجراء النهائي بناءً على حالة المراجعة اليدوية.
    """
    return "manual_review" if manual_review else summary_status


def _final_actionable_match(item, summary_status: str, outcome, match, config=None) -> bool:
    """
    Check if match is final and actionable (not blocked by manual review).
    التحقق مما إذا كانت المطابقة نهائية وقابلة للتنفيذ (غير محظورة بالمراجعة اليدوية).
    """
    return bool(match) and not manual_review_required(item, summary_status, outcome, config)


def text_block(title: str, row: dict[str, object]) -> str:
    """
    Return one readable text block for a structured artifact row.
    إرجاع كتلة نصية واحدة قابلة للقراءة لصف الأرتيفاكت الهيكلي.
    """
    body = "\n".join(f"{key}={value}" for key, value in row.items())
    return f"\n--- {title} ---\n{body}\n"


def blocked_candidate_query(outcome):
    """
    Return blocked candidate query from outcome.
    إرجاع استعلام المرشح المحظور من النتيجة.
    """
    from .order_blocked_candidate import blocked_candidate_query as _query
    return _query(outcome) if outcome else ""


# Main entry functions
# الدوال الرئيسية للدخول
def order_item_summary_row(item, summary, decision, outcome, config=None) -> dict[str, object]:
    """
    Return one compact row describing the final item outcome.
    إرجاع صف مضغوط يصف النتيجة النهائية للعنصر.
    """
    match_data = _get_match_data(decision, outcome)
    status = effective_order_status(summary.status, outcome)
    extraction_data = _prepare_extraction_data(
        status, match_data["match"], decision, match_data["blocked"], outcome, item, config
    )
    
    return _build_summary_row(
        item, summary, status, extraction_data["matched_query"],
        extraction_data["det_score"], outcome, match_data["match"],
        extraction_data["match_source"], extraction_data["blocked_candidate"],
        decision, extraction_data["manual_review"], config
    )


def _get_match_data(decision, outcome):
    """
    Get match and blocked candidate data.
    الحصول على بيانات المطابقة والمرشح المحظور.
    """
    from .order_blocked_candidate import blocked_ai_candidate
    
    match = decision.best_match if decision else None
    blocked = blocked_ai_candidate(outcome) if not match else {}
    return {"match": match, "blocked": blocked}


def _prepare_extraction_data(status, match, decision, blocked_candidate, outcome, item, config):
    """
    Prepare data for row extraction.
    تحضير البيانات لاستخراج الصف.
    """
    best_diagnostic, match_source, blocked_candidate = _extract_diagnostic_and_match(
        status, match, decision, blocked_candidate, outcome
    )
    manual_review = manual_review_required(item, status, outcome, config)
    matched_query, det_score = _extract_query_and_score(
        match, blocked_candidate, outcome, best_diagnostic
    )
    
    return {
        "match_source": match_source,
        "blocked_candidate": blocked_candidate,
        "manual_review": manual_review,
        "matched_query": matched_query,
        "det_score": det_score,
    }


def _build_summary_row(
    item, summary, status, matched_query, det_score, 
    outcome, match, match_source, blocked_candidate, 
    decision, manual_review, config
):
    """
    Build the final summary row dictionary.
    بناء قاموس صف الملخص النهائي.
    """
    row = _build_all_row_fields(
        item, summary, status, matched_query, det_score, outcome, match,
        match_source, blocked_candidate, decision, manual_review, config
    )
    row.update(_timing_fields(summary))
    return row


def _build_all_row_fields(item, summary, status, matched_query, det_score, outcome, match,
                          match_source, blocked_candidate, decision, manual_review, config):
    """
    Build all row fields except timing.
    بناء جميع حقول الصف ما عدا التوقيت.
    """
    imported_fields = _import_row_fields()
    final_action = _final_action(status, manual_review)
    row = _build_core_fields(
        item, summary, status, matched_query, det_score, outcome, match, config
    )
    row.update(_build_imported_fields(
        imported_fields, match_source, decision, match, summary,
        blocked_candidate, outcome, manual_review, final_action, status
    ))
    row.update(_build_diagnostic_fields(
        matched_query, match_source, decision, config, item, outcome
    ))
    return row


def _build_core_fields(item, summary, status, matched_query, det_score, outcome, match, config):
    """
    Build core item and match state fields.
    بناء الحقول الأساسية للعنصر وحالة المطابقة.
    """
    return {
        **_basic_item_fields(item, summary, status, matched_query, det_score),
        **_match_state_fields(item, status, outcome, match, config),
    }


def _build_imported_fields(imported_fields, match_source, decision, match, summary,
                           blocked_candidate, outcome, manual_review, final_action, status):
    """
    Build fields from imported helper functions.
    بناء الحقول من دوال المساعدة المستوردة.
    """
    return {
        **imported_fields["candidate"](match_source, decision, match, summary=summary),
        **imported_fields["blocked"](blocked_candidate),
        **imported_fields["ai"](outcome, manual_review, final_action),
        **imported_fields["review"](status, summary.reason, outcome),
    }


def _build_diagnostic_fields(matched_query, match_source, decision, config, item, outcome):
    """
    Build manufacturer and decision clarity diagnostic fields.
    بناء حقول تشخيص المصنع ووضوح القرار.
    """
    return {
        **_manufacturer_diagnostic_fields(matched_query, match_source, decision, config),
        **_decision_clarity_fields(item, decision, outcome),
    }


def _import_row_fields():
    """
    Import field extraction functions for summary row.
    استيراد دوال استخراج الحقول لصف الملخص.
    """
    from .order_blocked_candidate import blocked_candidate_fields
    from .order_summary_ai_fields import summary_ai_fields
    from .order_winner_fields import candidate_summary_fields
    from ..manual_review.manual_review_reason import manual_review_reason_fields
    
    return {
        "candidate": candidate_summary_fields,
        "blocked": blocked_candidate_fields,
        "ai": summary_ai_fields,
        "review": manual_review_reason_fields,
    }


def effective_order_status(summary_status, outcome):
    """
    Return effective order status considering AI outcome.
    إرجاع حالة الطلب الفعالة مع مراعاة نتيجة الذكاء الاصطناعي.
    """
    from .order_blocked_candidate import effective_order_status as _status
    return _status(summary_status, outcome)


# Manual review logic
# منطق المراجعة اليدوية
def manual_review_required(item, summary_status: str, outcome, config=None) -> bool:
    """
    Return whether this final item state needs human review.
    إرجاع ما إذا كانت هذه الحالة النهائية للعنصر تحتاج مراجعة بشرية.
    """
    from ..manual_review.manual_review_runtime import saved_manual_review_decision
    
    decision = saved_manual_review_decision(item)
    
    if decision and decision.manual_decision == "not_matching":
        return False
    
    if decision and decision.manual_decision in ("auto_matched", "approved_match"):
        return _check_re_review_needed(decision, summary_status, config)

    if outcome is not None and outcome.manual_review:
        return True
    
    return summary_status in REVIEWABLE_STATUSES


def _check_re_review_needed(decision, summary_status, config):
    """
    Check if re-review is needed for saved decisions.
    التحقق مما إذا كانت إعادة المراجعة مطلوبة للقرارات المحفوظة.
    """
    if summary_status in REVIEWABLE_STATUSES:
        re_review_key = (
            "enable_auto_match_re_review_on_fail"
            if decision.manual_decision == "auto_matched"
            else "enable_approved_match_re_review_on_fail"
        )
        if config and getattr(config, re_review_key, False):
            return True
    return False


def manual_review_row(item, summary, decision, outcome, config=None) -> dict[str, object]:
    """
    Return a manual-review row with empty human decision columns.
    إرجاع صف مراجعة يدوية مع أعمدة قرار بشرية فارغة.
    """
    row = order_item_summary_row(item, summary, decision, outcome, config)
    row.update(
        {
            "manual_review_reason_code": _manual_review_reason_code(row["status"], outcome),
            "manual_decision": "",
            "manual_reason": "",
            "correct_store_product_id": "",
        }
    )
    return row


# Match state logic
# منطق حالة المطابقة
def _match_state_fields(
    item, summary_status: str, outcome, match, config=None
) -> dict[str, object]:
    """
    Extract match state fields.
    استخراج حقول حالة المطابقة.
    """
    return {
        "matched": _final_actionable_match(
            item, summary_status, outcome, match, config
        ),
        "deterministic_match_found": bool(match),
        "manual_review_blocked_match": (
            bool(match) and
            manual_review_required(item, summary_status, outcome, config)
        ),
    }


def _final_actionable_match(item, summary_status: str, outcome, match, config=None) -> bool:
    """
    Check if match is final and actionable (not blocked by manual review).
    التحقق مما إذا كانت المطابقة نهائية وقابلة للتنفيذ (غير محظورة بالمراجعة اليدوية).
    """
    return bool(match) and not manual_review_required(item, summary_status, outcome, config)


# Public exports
__all__ = [
    "order_item_summary_row",
    "manual_review_required",
    "manual_review_row",
    "text_block",
    "REVIEWABLE_STATUSES",
    "SUMMARY_TIMING_KEYS",
]
