# بروتوكول الاختبار والتحقق

## الحالة قبل أي إصلاح

| الأمر | المتوقع قبل الإصلاح | النتيجة |
|---|---|---|
| `pytest tests/diagnostics/test_baraka_matching_hypotheses.py` | H1/H2 FAIL | 2 failed, 4 passed |
| `pytest tests/diagnostics/test_baraka_solution_scorecard.py` | precision gate FAIL | يعاد ضمن البوابة المجمعة |
| `pytest tests/core/excel_target/test_excel_target.py tests/test_product_matching.py` | PASS | لا يجب أن يتأثر بdiagnostics |

## نتائج التشغيل الفعلية بعد الإصلاح

- بوابة diagnostics وscorecard: `9 passed in 4.34s`.
- regression القريب: `66 passed, 8 subtests passed in 6.79s` لتشغيل Excel target وCLI target وproduct matching وmanual review.
- البوابة المجمعة المعتمدة: `87 passed, 8 subtests passed in 27.41s`.
- suite المشروع: `pytest -q tests` أنهى في `81.34s`: `21 failed, 974 passed, 19 skipped, 8 warnings, 134 subtests passed`.

الفشل الـ21 خارج نطاق Baraka/Excel-target ولم يُصلحها هذا التحقيق. من مجموعاتها: CLI contract، database migration، matching logging، swallow audit، no-results regression، وStreamlit Run DB. ظهرت أيضاً إشارة بيئية في اختبارات subprocess التي تقرأ مخرجات UTF-8 العربية بترميز cp1252، كما أن UI failures تشير إلى `st.button()` داخل `st.form()`. يجب تسجيل هذه failures كـbaseline منفصل، لا تحويلها إلى `xfail` ولا نسبتها إلى إصلاح Baraka.

تشغيل `pytest -q` بلا `tests` من جذر المشروع لم يكمل collection خلال 40 ثانية، لأنه يكتشف ملفات خارج suite؛ الأمر المعتمد في هذا التقرير هو `pytest -q tests`.

## بوابة التنفيذ بعد الموافقة

نفذ بالترتيب وتوقف عند أول failure:

```powershell
# السبب + scorecard
.\.venv\Scripts\python.exe -m pytest -q tests\diagnostics\test_baraka_matching_hypotheses.py tests\diagnostics\test_baraka_solution_scorecard.py

# regression قريب
.\.venv\Scripts\python.exe -m pytest -q tests\cli\commands\test_excel_target_e2e.py tests\test_product_matching.py tests\core\manual_review
```

تم تشغيل هذه الاختبارات بنجاح بعد الإصلاح:
- diagnostics وscorecard: 9 passed.
- regression القريب: 66 passed, 8 subtests.
- إجمالي بوابة المطابقة: 87 passed, 8 subtests بنسبة 100%.

## Replay checklist

لكل `matched-only` في Excel summary بعد التنفيذ:

- [x] الاسم يحمل brand مثبت، لا pack/form فقط.
- [x] `identity_evidence` يوضح native English أو dictionary أو cached translation أو `tawreed_catalog` المرتبط بصف Baraka أو manual decision محدد.
- [x] strength/form/pack متوافقة.
- [x] لا يوجد `No extra numeric tokens` كسبب قبول وحيد.
- [x] عند غياب الدليل تكون الحالة no-results/manual review.

## سلامة worktree

كان worktree غير نظيف قبل التحقيق ويحتوي تعديلات matcher/config/artifacts/state. لذلك تُذكر الملفات التالية كمدخلات التحقيق، ولا يعني ذلك أن باقي worktree لم يتغير:

```text
tests/diagnostics/test_baraka_matching_hypotheses.py
tests/diagnostics/test_baraka_solution_scorecard.py
docs/baraka_matching_investigation_20260906/
```

قبل التنفيذ راجع `git diff` كي لا يختلط الإصلاح مع تعديلات العمل السابقة.
