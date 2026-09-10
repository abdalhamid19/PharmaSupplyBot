# تحليل توسعة `identity_absent` إلى Manual Review

## النطاق والنتيجة المختصرة

هذا التحليل يقتصر على مسار Excel-target عندما تكون النتيجة `no-results`، مع
التركيز على الحالة التي لا توجد فيها هوية موثقة (`identity_absent`) لكن يوجد
مرشح موثوق من review discovery. لم يتم تعديل كود الإنتاج.

**النتيجة:** في النسخة الحالية، السلوك المطلوب موجود بالفعل. فوجود
`identified == ()` لا يمنع manual review إذا أعاد discovery مرشحًا؛ القرار في
مسار CLI يعتمد على `candidate_count_total > 0`. لذلك التعديل الآمن المقترح
للمرحلة التالية هو اختبار regression صريح، وليس توسيع المطابقة التلقائية أو
تغيير `manual_review_required` العامة.

## Data-flow / تتبع المسار

1. **ExcelTargetMatcher** — في
   `src/core/excel_target/excel_target_matching.py:89-129`:

   - يحاول أولًا الهوية الموثقة عبر `identity_index.identify`.
   - إذا لم ينتج match آمنًا، ينفّذ `review_discovery.discover`.
   - يمرر `discovery_hits` إلى `build_review_candidates` حتى عندما تكون
     `identified` فارغة.
   - مرشحو discovery يظلون review-only؛ مسار `_compatible_identified` لا
     يستقبلهم، و`_identity_decision` يمنع أصلًا `review_fuzzy` من إنتاج
     auto-match (`excel_target_matching.py:188-202, 401-405`).

2. **Review discovery** — في
   `src/core/excel_target/excel_target_review_discovery.py:145-185`:

   - يختار projection إنجليزيًا أو عربيًا، ثم يطبق shared-brand-token وعتبات
     score/margin.
   - الحالات المقبولة للمراجعة هي `strong`, `medium`, `ambiguous`، مع إبقاء
     تعارضات variant كمرشحين للمراجع (`review_discovery.py:215-239,
     242-260`).
   - هذه الطبقة لا تتصل بالشبكة ولا تغيّر قرار المطابقة.

3. **Candidate assembly** — في
   `src/core/excel_target/excel_target_review_candidates.py:165-273`:

   - يضيف discovery hits كـ `identity_evidence.kind = review_fuzzy`.
   - يتحقق من أن الصف موجود في نفس workbook/catalog عبر `catalog_row_keys`؛
     وهذا يمنع تسرب مرشح Tawreed إلى Excel target آخر.
   - يحافظ على `source_file`, `source_row_number` و`excel_target_row_key`.

4. **CLI artifact decision** — في
   `src/cli/commands/cli_order_excel_target.py:278-413`:

   - عند `decision.best_match is None` يجمع كل المرشحين ثم يحسب:

     ```python
     candidate_count_total = len(all_review_candidates)
     review_required = candidate_count_total > 0
     ```

   - إذا كان هناك discovery candidate فقط، تصبح النتيجة:
     `manual_review_required=True` و`manual_review_category=
     excel_target_candidate_available`.
   - إذا لم يوجد أي مرشح، تبقى الفئة `identity_absent` أو
     `identity_variant_rejected` عبر
     `cli_order_excel_target.py:573-575`.

5. **Important distinction:** الدالة العامة
   `src/core/ordering/order_run_artifact_rows.py:28-40` لا تقرر هذه الحالة في
   مسار Excel-target match-only؛ هذا المسار يكتب flag الخاص به مباشرة في
   `cli_order_excel_target.py`. لذلك تعديل الدالة العامة سيكون أوسع من نطاق
   المرحلة وغير مطلوب.

## Current safety assessment

| الحالة | `identified` | `review_candidates` | النتيجة الحالية |
|---|---:|---:|---|
| هوية موثقة وvariant مرفوض | موجودة | موجودة | manual review |
| هوية غير موجودة وdiscovery موثوق | فارغة | موجودة | manual review |
| هوية غير موجودة ولا discovery | فارغة | فارغة | لا manual review؛ `identity_absent` |
| discovery candidate فقط | فارغة | موجودة | لا auto-match، manual review فقط |

هذا يحقق boundary المطلوب: زيادة وصول الحالات القابلة للفحص البشري دون
إدخال fuzzy discovery في `best_match`.

## التعديل الصغير الآمن المقترح

لا أوصي حاليًا بتعديل سلوك الإنتاج؛ السلوك موجود بالفعل. التعديل الآمن هو
إضافة regression test يثبت العقد التالي:

```text
identity absent + no-results + reliable discovery hit
    => manual_review_required=True
    => candidate artifact exists
    => decision.best_match is None
```
إذا أظهرت نتيجة الاختبار فجوة في فرع مستقبلي، يكون التغيير الأدنى هو استخراج
predicate محلي داخل `cli_order_excel_target.py`، مع إبقاء نفس السياسة:

```python
def _excel_target_review_required(result) -> bool:
    return result.decision.best_match is None and bool(result.review_candidates)
```

ثم استخدامه بدل الشرط inline. هذا يحسن الوضوح ويمنع أن يتحول `identity_absent`
إلى review لمجرد عدم وجود هوية؛ لا يضيف أي auto-match ولا يخفض thresholds.

## TDD proposal / اختبارات مقترحة

أضف الاختبار إلى
`tests/cli/commands/test_excel_target_manual_review_artifacts.py`:

1. جهّز catalog لا يملك alias/identity موثقًا للطلب.
2. اعترض `ExcelTargetReviewDiscoveryIndex.discover` ليعيد
   `ReviewDiscoveryHit` مضبوطًا بحالة `strong` أو `medium`، مع صف من نفس
   catalog.
3. شغّل `run_excel_target_match_only` عبر artifact temp directory.
4. assertions:
   - `totals["manual_review"] == 1`.
   - CSV يحتوي `manual_review_required == "True"`.
   - الفئة `excel_target_candidate_available` وليست `identity_absent`.
   - JSONL يحتوي candidate method `english_fuzzy` أو `arabic_fuzzy`، وsource
     file/row key الصحيحين.
   - لا يوجد `best_match` تلقائي في نتيجة matcher.
5. احتفظ بالاختبار الموجود
   `test_no_identity_candidate_does_not_enter_manual_review` كـ negative
   control؛ يجب أن يبقى `manual_review == 0` عندما لا يوجد discovery hit.
6. أعد اختبارات discovery الموجودة في
   `tests/core/excel_target/test_excel_target_review_discovery.py:15-215`،
   خصوصًا unrelated-name وambiguous وvariant-conflict، للتأكد من أن زيادة
   التغطية لا ترفع noise أو تزيل المرشحين المختلفين.

## Acceptance criteria

- discovery-only identity-absent rows تظهر في manual review artifacts.
- unrelated/no-hit identity-absent rows لا تظهر تلقائيًا في manual review.
- `decision.best_match` لا يتغير بسبب discovery.
- لا تعديل على `manual_review_required` العامة أو على automatic identity.
- provenance للـ target/source/row محفوظ كما هو.

## Evidence / الأدلة المعتمدة

- `src/core/excel_target/excel_target_matching.py:89-129, 188-202, 401-405`
- `src/core/excel_target/excel_target_review_discovery.py:24-45, 145-185, 215-260`
- `src/core/excel_target/excel_target_review_candidates.py:165-273`
- `src/cli/commands/cli_order_excel_target.py:135-175, 278-413, 555-575`
- `src/core/ordering/order_run_artifact_rows.py:28-40`
- `tests/cli/commands/test_excel_target_manual_review_artifacts.py:63-104`
- `tests/core/excel_target/test_excel_target_review_discovery.py:15-215`
- `tests/core/excel_target/test_coverage.py:78-149`

تم تشغيل الاختبارات المرتبطة بالتحليل:

```text
23 passed in 8.18s
```
