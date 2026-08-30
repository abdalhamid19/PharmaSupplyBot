# 04 — تنفيذ الإصلاح: الكود قبل/بعد (Fix Implementation)

> جميع التعديلات في 3 ملفات مصدرية. كل مقطع يعرض قبل (buggy) وبعد (fixed) مع شرح سطر بسطر.

---

## الملف 1: `src/tawreed/order/tawreed_order_summary_build.py`

### 1.1 الرأس (استيراد logger)

**قبل:**
```python
from __future__ import annotations

from src.core.artifact_run import current_artifact_run
```

**بعد:**
```python
from __future__ import annotations

import logging

from src.core.artifact_run import current_artifact_run
# ...
logger = logging.getLogger(__name__)
```

**السبب:** التخطيات في الحفظ التلقائي كانت صامتة تماماً؛ الآن تُسجَّل بـ `logger.info` مع كود الصنف واسمه وسبب التخطي.

### 1.2 نقطة الاستدعاء تمرر الـ config

**قبل:**
```python
elif matching_config and matching_config.enable_auto_save_verified_match:
    _auto_save_verified_match(item, decision)

def _auto_save_verified_match(item: Item, decision) -> None:
```

**بعد:**
```python
elif matching_config and matching_config.enable_auto_save_verified_match:
    _auto_save_verified_match(item, decision, matching_config)

def _auto_save_verified_match(item: Item, decision, matching_config=None) -> None:
```

**السبب:** الحل يحتاج قراءة `enable_manufacturer_check` من إعدادات المستخدم — يجب تمرير الـ config للدالة.

### 1.3 قلب الإصلاح — الحارس

**قبل (الخطأ):**
```python
    # Safety check: skip saving matches that have validation issues
    from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
    if should_skip_auto_save_verified_match(item, match.data, getattr(decision, 'rejection_reason', None)):
        return

    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
```

**بعد (الإصلاح):**
```python
    # Safety check: skip saving matches that have validation issues.
    # The helper returns (should_skip, reason); unpack it — the previous
    # bare `if <tuple>:` was always truthy and blocked every auto-save,
    # so nothing was ever persisted as auto_matched.
    from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
    rejection_reason = _decision_rejection_reason(decision)
    skip, skip_reason = should_skip_auto_save_verified_match(
        item,
        match.data,
        rejection_reason,
        enable_manufacturer_check=bool(
            matching_config and matching_config.enable_manufacturer_check
        ),
    )
    if skip:
        _log_auto_save_skip(item, skip_reason)
        return

    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
```

**الفروقات الثلاثة الحاسمة:**

| # | قبل | بعد | الأثر |
|---|---|---|---|
| 1 | `if helper(...):` — tuple دائماً truthy → return دائماً | `skip, skip_reason = helper(...)` ثم `if skip:` — قيمة منطقية حقيقية | **الحفظ يعمل** |
| 2 | `getattr(decision, 'rejection_reason', None)` — دائماً None (الحقل غير موجود على MatchDecision) | `_decision_rejection_reason(decision)` — يقرأ سبب الرفض من أفضل diagnostic | الحماية من الرفض الصريح **تفعلت فعلياً** لأول مرة |
| 3 | تخطٍ صامت | `_log_auto_save_skip(item, skip_reason)` | أي تخطٍ مستقبلي مرئي في logs |

### 1.4 الدوال المساعدة الجديدة

```python
def _decision_rejection_reason(decision) -> str | None:
    """Return the winning diagnostic's rejection reason, when it is negative.

    MatchDecision has no rejection_reason field; the signal lives on the best
    CandidateMatchDiagnostic. Only a genuine rejection reason is surfaced —
    an accepted candidate's empty string must not block auto-save.
    """
    diagnostics = getattr(decision, "diagnostics", None) or []
    best = max(diagnostics, key=lambda diagnostic: diagnostic.score, default=None)
    reason = getattr(best, "rejection_reason", "") if best else ""
    return reason or None


def _log_auto_save_skip(item: Item, reason: str) -> None:
    """Log why an auto-save was skipped so silent data loss stays visible."""
    logger.info(
        "auto-save skipped",
        extra={"code": item.code, "item_name": item.name, "reason": reason},
    )
```

**نقاط دقيقة:**
- `max(..., default=None)` يتعامل مع `diagnostics=[]` بأمان.
- `reason or None` يحول `""` (المقبول) إلى `None` حتى لا يُفعّل فحص الكلمات المفتاحية بالخطأ.
- فلترة `best` على `score` وليس `accepted` لأن الأهم هو سبب رفض المرشح الفائز.

---

## الملف 2: `src/core/manual_review/manual_review_helpers.py`

### قبل (الخطأ):
```python
def should_skip_auto_save(
    item: Item,
    candidate: dict,
    rejection_reason: str | None = None,
) -> tuple[bool, str]:
    ...
    # Skip if there's a conflict-related rejection reason
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
```

### بعد (الإصلاح):
```python
def should_skip_auto_save(
    item: Item,
    candidate: dict,
    rejection_reason: str | None = None,
    enable_manufacturer_check: bool = False,     # ← جديد
) -> tuple[bool, str]:
    ...
    # Skip if there's a conflict-related rejection reason
    if rejection_reason:
        rejection_lower = rejection_reason.lower()
        conflict_keywords = ["conflict", "manufacturer", "brand", "semantic"]
        if any(keyword in rejection_lower for keyword in conflict_keywords):
            return True, f"Conflict-related rejection: {rejection_reason}"

    # Heuristic manufacturer conflict — opt-in only (see docstring).
    if enable_manufacturer_check:                 # ← جديد: بوابة
        item_manufacturer = _extract_item_manufacturer(item)
        candidate_manufacturer = _extract_candidate_manufacturer(candidate)

        if item_manufacturer and candidate_manufacturer:
            if manufacturer_conflict(item_manufacturer, candidate_manufacturer):
                return True, (
                    f"Manufacturer conflict detected for auto-save: "
                    f"item '{item_manufacturer}' vs candidate '{candidate_manufacturer}'"
                )

    return False, "No conflicts detected"
```

**السبب:** الفحص التقريبي (آخر كلمة في الاسم = الشركة) ينتج رفضاً وهمياً لمعظم الأصناف:
```
'PANADOL EXTRA 24 TAB' → 'EXTRA'  vs companyName 'GSK'  → "conflict" ❌
'ULTRA PANADOL 10 TAB' → 'PANADOL' (اسم تجاري)          → "conflict" ❌
```
الفلاغ `enable_manufacturer_check` **موجود أصلاً** في `MatchingConfig` كفلاغ عام — الآن يستخدمه الفحص بدل التشغيل الدائم. الافتراضي `False` = سلوك آمن، والمستخدم يفعّله صراحة إن أراد.

> ملاحظة: حماية "سبب الرفض الصريح" (الفقرة الأولى) بقيت دائمة — هي إشارة موثوقة من محرك المطابقة، وليست تقريباً اسمياً.

---

## الملف 3: `src/core/manual_review/manual_review_runtime.py`

**قبل:**
```python
def should_skip_auto_save_verified_match(
    item: Item,
    candidate: dict,
    rejection_reason: str | None = None,
) -> tuple[bool, str]:
    ...
    return should_skip_auto_save(item, candidate, rejection_reason)
```

**بعد:**
```python
def should_skip_auto_save_verified_match(
    item: Item,
    candidate: dict,
    rejection_reason: str | None = None,
    enable_manufacturer_check: bool = False,       # ← جديد
) -> tuple[bool, str]:
    ...
    return should_skip_auto_save(
        item, candidate, rejection_reason, enable_manufacturer_check
    )
```

**السبب:** الـ wrapper هو الواجهة العامة المستخدمة في `_auto_save_verified_match` — يجب أن يمرر الفلاغ الجديد.

---

## سلوك ما بعد الإصلاح (مصفوفة القرار)

| الحالة | سلوك ما بعد الإصلاح | سبب الحفظ/التخطي |
|---|---|---|
| تطابق سليم (أي اسم) | ✅ يُحفظ `auto_matched` | skip=False |
| سبب رفض تضارب صريح في diagnostics | ⛔ تخطٍ + log | "Conflict-related rejection" |
| score=999 + "Approved by saved manual review" | ⛔ تخطٍ (بدون حفظ مكرر) | حارس القرار المخزَّن |
| يوجد قرار بشري سابق approved_match/not_matching | ⛔ تخطٍ (بدون كدس) | `_preserve_existing_decision` |
| status قابل للمراجعة (no-results...) | → مسار المراجعة البشرية | `manual_review_required` |
| `enable_auto_save_verified_match=False` | ⛔ لا حفظ تلقائي إطلاقاً | فلاغ المستخدم |
| `enable_manufacturer_check=True` + تضارب اسمي فعلي | ⛔ تخطٍ + log | opt-in فحص الشركة |

---

## إحصائية الـ diff النهائي

```
 src/core/manual_review/manual_review_helpers.py  | 34 ++++++++------
 src/core/manual_review/manual_review_runtime.py  | 12 ++++++-
 src/tawreed/order/tawreed_order_summary_build.py | 46 ++++++++++++---
 3 files changed, 77 insertions(+), 15 deletions(-)
```
