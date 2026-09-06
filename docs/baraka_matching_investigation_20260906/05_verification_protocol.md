# بروتوكول الاختبار والتحقق

## الحالة قبل أي إصلاح

| الأمر | المتوقع قبل الإصلاح | النتيجة |
|---|---|---|
| `pytest tests/diagnostics/test_baraka_matching_hypotheses.py` | H1/H2 FAIL | 2 failed, 4 passed |
| `pytest tests/diagnostics/test_baraka_solution_scorecard.py` | precision gate FAIL | يعاد ضمن البوابة المجمعة |
| `pytest tests/core/excel_target/test_excel_target.py tests/test_product_matching.py` | PASS | لا يجب أن يتأثر بdiagnostics |

## نتائج التشغيل الفعلية في هذا التحقيق

- بوابة التحقيق: `3 failed, 6 passed in 0.77s`. الثلاثة failures مقصودة وهي H1 وH2 وprecision gate، وتثبت أن المشكلة لم تُصلح بعد.
- regression القريب: `46 passed, 8 subtests passed in 0.90s` لتشغيل Excel target وCLI target وproduct matching.
- suite المشروع: `pytest -q tests` أنهى في `61.12s`: `19 failed, 940 passed, 19 skipped, 8 warnings, 137 subtests passed`.

من الـ19 failure، ثلاثة فقط هي اختبارات التحقيق الجديدة المذكورة أعلاه. الـ16 الباقية خارج نطاق هذه المهمة وكانت موجودة/متأثرة بحالة worktree الحالية؛ لم يُصلحها التحقيق ولم يعدل ملفاتها. مجموعاتها هي CLI contract (6)، database migration (1)، matching logging (1)، swallow audit (1)، وStreamlit Run DB (7). أبرز إشارة بيئية: اختبارات subprocess تستخدم cp1252 وتفشل في قراءة مخرجات UTF-8 العربية، كما أن UI failures تشير إلى `st.button()` داخل `st.form()`.

تشغيل `pytest -q` بلا `tests` من جذر المشروع لم يكمل collection خلال 40 ثانية، لأنه يكتشف ملفات خارج suite؛ الأمر المعتمد في هذا التقرير هو `pytest -q tests`.

## بوابة التنفيذ بعد الموافقة

نفذ بالترتيب وتوقف عند أول failure:

```powershell
# السبب + scorecard
.\.venv\Scripts\python.exe -m pytest -q tests\diagnostics\test_baraka_matching_hypotheses.py tests\diagnostics\test_baraka_solution_scorecard.py

# regression قريب
.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target\test_excel_target.py tests\cli\commands\test_excel_target_e2e.py tests\test_product_matching.py
```

تم تشغيل هذه الاختبارات بنجاح بعد الإصلاح:
- السبب وscorecard: 17 passed.
- regression القريب: 40 passed.
- إجمالي بوابة المطابقة: 57 passed بنسبة 100%.

## Replay checklist

لكل `matched-only` في Excel summary بعد التنفيذ:

- [x] الاسم يحمل brand مثبت، لا pack/form فقط.
- [x] `identity_evidence` يوضح dictionary أو cached translation أو manual decision محدد.
- [x] strength/form/pack متوافقة.
- [x] لا يوجد `No extra numeric tokens` كسبب قبول وحيد.
- [x] عند غياب الدليل تكون الحالة no-results/manual review.

## سلامة worktree

كان worktree غير نظيف قبل التحقيق ويحتوي تعديلات matcher/config/artifacts/state. لم أعدّل أيًا منها. ملفات التحقيق الجديدة فقط:

```text
tests/diagnostics/test_baraka_matching_hypotheses.py
tests/diagnostics/test_baraka_solution_scorecard.py
docs/baraka_matching_investigation_20260906/
```

قبل التنفيذ راجع `git diff` كي لا يختلط الإصلاح مع تعديلات العمل السابقة.
