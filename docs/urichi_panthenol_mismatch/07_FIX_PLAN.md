# 7 — خطة الحل الكاملة المرتبة

هذه خطة تنفيذ جراحية صغيرة، ملتزمة بتعليمات `docs/project_guidelines.md` و`docs/starting_prompt.md`: أقل تعديل يحل السبب الأساسي، مع tests قبل/بعد، ودون refactor غير مطلوب.

## الهدف القابل للتحقق

يجب أن تتحقق الشروط التالية بعد الإصلاح:

1. `U RICHI PANTHENOL ADVANCE CREAM GEL 50M` يطابق candidate:
   `U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM`.
2. لا تظهر رسالة:
   `Semantic token conflict: CREAM vs GEL, GEL vs CREAM`
   عندما تكون forms في query والcandidate متطابقة `{CREAM, GEL}`.
3. تبقى حالات التعارض الحقيقية مرفوضة، مثل `CREAM` مقابل `LOTION` أو `ANISE` مقابل `DETOX`.
4. كل اختبارات المشروع تعمل.
5. `tools/rule_audit.py` ينجح.

## المرحلة 1: اختبار يكشف الخطأ الحالي

### ملف test مقترح

`tests/test_product_matching.py`

### Test 1: حالة U RICHI كاملة

اختبار قبل الإصلاح يجب أن يفشل حالياً، وبعد الإصلاح ينجح:

```python
def test_compound_cream_gel_match_is_not_rejected_as_conflict(self) -> None:
    item = Item("91167", "U RICHI PANTHENOL ADVANCE CREAM GEL 50M", 1)
    decision = explain_best_product_match(
        item,
        [
            (
                item.name,
                [
                    _candidate(
                        "U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM",
                        "يو ريتشي بانثينول ادفانس كريم جل 50 جم",
                    )
                ],
            )
        ],
    )

    self.assertIsNotNone(decision.best_match)
    self.assertEqual(
        decision.best_match.data["productNameEn"],
        "U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM",
    )
```

صيغة helper الحالية في `tests/test_product_matching.py` لا تقبل `store_product_id` كوسيط، لكنها تضيف `storeProductId` تلقائياً بصيغة `store-{english_name}`؛ لذلك لا يلزم تمرير وسيط إضافي.

### Test 2: رفض تعارض حقيقي ما زال يعمل

يجب التأكد أن test موجود بالفعل:

```python
def test_semantic_conflict_rejects_isis_detox_for_anise(self) -> None:
    ...
```

لو موجود، يكفي تشغيله. إذا لم يغطي form conflict، أضف test صغير:

```python
def test_form_conflict_still_rejects_cream_for_lotion(self) -> None:
    item = Item("1", "ABC CREAM 50 GM", 1)
    decision = explain_best_product_match(
        item,
        [(item.name, [_candidate("ABC LOTION 50 GM", "...")])],
    )
    self.assertIsNone(decision.best_match)
    self.assertIn("Semantic token conflict", decision.final_reason)
```

## المرحلة 2: تعديل جراحي في `_semantic_conflicts`

### الملف

`src/core/matching/matching_penalties.py`

### التعديل المقترح

```python
def _semantic_conflicts(
    query_tokens: set[str], candidate_tokens: set[str]
) -> set[tuple[str, str]]:
    conflicts: set[tuple[str, str]] = set()
    for group in CONFLICT_GROUPS:
        query_group = query_tokens & group
        candidate_group = candidate_tokens & group
        if query_group == candidate_group:
            continue
        conflicts.update(
            (left, right) for left in query_group for right in candidate_group
        )
    return {(left, right) for left, right in conflicts if left != right}
```

### لماذا هذا آمن؟

لأننا لا نلغي conflict إلا عندما تكون tokens داخل نفس conflict group متطابقة تماماً بين الطرفين.

أمثلة:

| query | candidate | النتيجة بعد الإصلاح |
|------|-----------|--------------------|
| CREAM GEL | CREAM GEL | لا conflict |
| CREAM | GEL | conflict |
| CREAM | LOTION | conflict |
| ANISE | DETOX | conflict |
| APPLE | ORANGE | conflict |

## المرحلة 3: تحسين Manual Review Top-N (اختياري لكنه موصى به)

بعد إصلاح السبب الأساسي، التشغيل الجديد يجب أن يطابق تلقائياً. لكن artifacts القديمة ستظل تعرض options خاطئة لأنها مكتوبة قبل الإصلاح.

تحسين مقترح لاحق:

- في `review_candidate_options()`، بدلاً من `decision.diagnostics[:limit]` فقط، أضف candidates rejected ذات overlap عالي.
- أو أضف `include_high_similarity_rejections=True`.
- اكتب test يثبت أن candidate الصحيح يظهر في options حتى لو rejected بسبب rule.

هذا ليس ضرورياً لإصلاح المطابقة الأساسية، لكنه يحسن Manual Review.

## المرحلة 4: التعامل مع Saved Correction

### لا تغيّر سلوك `needs_correction` في الإصلاح الأول

السبب: تغيير `needs_correction` إلى forced match قد يضيف مخاطر. التعديل الأصغر والأصح هو إصلاح rule الذي يرفض candidate الصحيح.

### بعد الإصلاح

لو `correct_query` محفوظ:

```
U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
```

فسيبدأ البحث بهذا query، ومن المتوقع أن يقبل candidate الصحيح إذا رجع ضمن نتائج البحث ولم تمنعه قاعدة أخرى، لأن `CREAM GEL` لن يُرفض بسبب التعارض الذاتي.

## المرحلة 5: تشغيل الاختبارات

نفّذ:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -q
.\.venv\Scripts\python tools\rule_audit.py
```

إذا فشل test بسبب import أو helper signature، لا تغيّر السلوك؛ عدّل test ليتوافق مع existing helper فقط.

## المرحلة 6: التحقق العملي على صنف واحد

بعد نجاح unit tests، شغّل match-only أو order محدود لصنف 91167 إذا كان الملف المدخل متاحاً.

أمثلة محتملة حسب CLI المتاح:

```powershell
.\.venv\Scripts\python run.py order --excel "data/input/order_items/shortage_report_total_20260623.xlsx" --profile wardany --limit 1 --debug-browser
```

أو استخدم ملف صغير يحتوي الصنف فقط إن كان موجوداً.

معيار النجاح العملي:

- لا يظهر `No decisive match found` للصنف.
- يظهر match product name:
  `U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM`.
- لا تظهر الخيارات الخاطئة كـ best candidates في artifacts الجديدة.

## المرحلة 7: توثيق النتيجة

حدّث هذا التقرير أو أضف `09_FIX_RESULT.md` بعد التنفيذ يتضمن:

1. الملفات المعدلة.
2. الاختبارات التي أضيفت.
3. مخرجات test command.
4. أي قيود متبقية مثل artifacts القديمة لا تتغير تلقائياً.
