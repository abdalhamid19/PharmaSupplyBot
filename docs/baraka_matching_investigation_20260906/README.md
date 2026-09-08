# تحقيق مطابقة «البركة شركات»

هذا المجلد يوثق التحقيق والإصلاح واختبارات الاختيار. الإصلاح لا يضيف أي منتج من Tawreed إلى كتالوج البركة؛ بل يستخدم `tawreed_products.csv` كمصدر alias ثنائي اللغة فقط عندما يوجد الصف العربي نفسه في كتالوج البركة.

## النتيجة المختصرة

التحقيق أثبت مرحلتين مختلفتين: الإصلاح السابق كان ضرورياً لمنع false positives، لكنه ترك recall منخفضاً لأن Excel-target لم يكن يستفيد من `data/input/dictionaries/tawreed_products.csv`. الحل الحالي يضيف aliases Tawreed إلى فهرس الهوية فقط، ثم يطلب وجود صف Baraka نفسه ويمرره عبر فحص التركيز والشكل والعبوة. ملف Tawreed لا يثبت التوفر أو السعر في البركة.

ابدأ من [01_reproduction_and_evidence.md](01_reproduction_and_evidence.md)، ثم [02_hypotheses_and_scores.md](02_hypotheses_and_scores.md)، ثم [07_tawreed_alias_integration.md](07_tawreed_alias_integration.md). نتائج الاختبارات والمقارنة في [08_solution_verification.md](08_solution_verification.md)، والخطة التنفيذية المحدثة في [09_complete_plan.md](09_complete_plan.md). سجل التنفيذ الفعلي في [06_implementation_verification.md](06_implementation_verification.md).

## ملفات الاختبار

- `tests/diagnostics/test_baraka_matching_hypotheses.py`: اختبارات سبب المشكلة.
- `tests/diagnostics/test_baraka_solution_scorecard.py`: عقد اختيار الحل.
- `tests/core/excel_target/test_baraka_safe_matching.py`: اختبار alias Tawreed، منع false positive، وحفظ variants.
- `tests/core/excel_target/test_coverage.py`: تصنيف الهوية والـvariant rejection.
- `scripts/baraka_coverage_report.py`: تقرير CSV/JSONL offline لكل item بدون ترجمة حيّة.
- `scripts/baraka_index_benchmark.py`: قياس بناء الفهرس وزمن مطابقة 50 item.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\diagnostics\test_baraka_matching_hypotheses.py tests\diagnostics\test_baraka_solution_scorecard.py
```

بعد الإصلاح لا يجوز تحويل هذه الاختبارات إلى `xfail` أو حذفها؛ نجاحها هو تعريف حل المشكلة. آخر بوابة موثقة: `87 passed, 8 subtests passed in 27.41s`. أما `pytest -q tests` العامة فسجلت آخر مرة `21 failed, 974 passed, 19 skipped, 8 warnings, 134 subtests passed`؛ هذه failures مستقلة عن Baraka.

في آخر replay لأول 50 صفاً، النتيجة `13 matched-only` و`37 no-results`. هذا لا
يثبت غياب 37 منتجاً من Baraka؛ هو قرار أمان، وتفصيله موثق في ملفات التحقق:
29 نقص دليل هوية و8 حالات هوية موجودة لكن variant غير متوافق. أصبحت الأدلة
موجودة في CSV/JSONL حتى لحالات الرفض، فلا يختلط غياب الهوية مع رفض الخصائص.

بعد نجاح replay تم تشغيل الأمر الأصلي مع `--all-profiles --match-only`؛ اكتمل
دون cart mutation، وسجل Tawreed 47 match و1 flagged، وسجل Baraka 13 match و37
no-results. تفاصيل التشغيل النهائي في [06_implementation_verification.md](06_implementation_verification.md).
# Latest implementation addendum (2026-09-07, run 20260907_1752)

This addendum supersedes older replay numbers in this folder. The implemented
Manual Review provenance pipeline was verified with the original Baraka command:

- Baraka: 50 processed, 13 `matched-only`, 37 `no-results`.
- 8 of the 37 no-results rows have Baraka-only review candidates and are now
  persisted as `manual_review_required=1`.
- Candidate artifacts contain only Excel Target products. Every candidate has
  `matching_source=excel-target`, target key/file, identity evidence, and the
  compatibility rejection reason.
- The run produced `manual_review_excel-target_*.csv` and
  `manual_review_candidates_excel-target_*.jsonl`, which are discovered by the
  Manual Review page. Saved Corrections now exposes `manual_decision`,
  `matching_source`, `matching_source_label`, and identity evidence.
- A table-based approval also preserves this provenance and stores
  `manual_decision=approved_match`; verified automatic matches use
  `manual_decision=auto_matched`.

Focused Baraka/Excel Target/Manual Review/database gate: **146 passed**.
Diagnostic and reproduction gate: **24 passed**. The full repository suite was
also run: **987 passed, 21 failed, 19 skipped**. The 21 failures are existing
out-of-scope CLI/encoding, order-runs migration, matching hypothesis, swallow
audit, and Run DB Streamlit tests; no Baraka/Excel Target gate failed.
