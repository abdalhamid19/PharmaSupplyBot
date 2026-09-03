# 04 — شبكة أمان الاختبارات (Testing Checklist)

> نفّذ هذه القائمة **بعد كل مهمة** من 02-plan.md، وليس فقط في النهاية.

## 1. الاختبار السريع (بعد كل مهمة — دقيقتان)

```powershell
# 1. order يعمل؟ (الاختبار الأهم إطلاقًا)
.venv\Scripts\python.exe run.py order --help

# 2. لا استيرادات مكسورة في src
.venv\Scripts\python.exe -m compileall src -q

# 3. مجموعة الاختبارات
.venv\Scripts\python.exe -m pytest tests/ -q -x
```

**معايير النجاح:**
- ✅ `order --help` يعرض كل الخيارات بما فيها `--match-only` و `--matching-risk-policy`
- ✅ compileall بلا أخطاء
- ✅ pytest بلا فشل (لاحظ: مهام 2-3 ستكسر بعض اختبارات cli/ui المؤقتًا — إذا نُفذت قبل Task 5. البديل الآمن: نفّذ حذف اختبارات match-products في Task 5 فورًا بعد كل مهمة بدل تجميعها)

## 2. قائمة التحقق الوظيفية لـ order (قبل الـ PR)

| # | التحقق | الأمر/الطريقة | متوقع |
|---|---|---|---|
| 1 | أوامر CLI الأربعة موجودة | `py run.py --help` | auth, order, remove-cart, export-products |
| 2 | match-products محذوف | `py run.py match-products` | Error: No such command |
| 3 | خيارات order سليمة | `py run.py order --help` | كل الخيارات بما فيها --match-only |
| 4 | محرك matching الداخلي يعمل | `python -c "from src.core.matching.product_matching import explain_best_product_match; print('ok')"` | ok |
| 5 | normalization الجديد يعمل | `python -c "from src.core.normalization.normalizer import parse_drug; print(parse_drug('panadol extra 500mg'))"` | نتيجة parse صحيحة |
| 6 | config لا يزال يُقرأ | `python -c "from src.core.config.config import load_config; c=load_config('config.yaml'); print(type(c.matching))"` | MatchingConfig |
| 7 | identity يعمل | `python -c "from src.core.identity.manufacturer_identity import manufacturer_conflict; print('ok')"` | ok |
| 8 | قاعدة البيانات | `python -c "from src.core.database.order_runs_meta import *; print('ok')"` | ok |
| 9 | Streamlit يفتح | `py -m streamlit run streamlit_app.py` | 8 تابات، بلا crash |
| 10 | تاب Results | افتح التاب | القائمة: order, export-products, remove-cart فقط |
| 11 | Manual Review search | زر "Search Corrected Items" | يبني أمر `order --match-only` (وليس match-products) |

## 3. اختبارات pytest المستهدفة (خرائط الملفات)

### اختبارات يجب أن تمر دائمًا (منطقة order المحمية)
```powershell
.venv\Scripts\python.exe -m pytest tests/core/matching/ tests/core/test_logging_audit.py -q
.venv\Scripts\python.exe -m pytest tests/core/normalization/ -q        # بعد Task 5
.venv\Scripts\python.exe -m pytest tests/test_co_avazir_mismatch.py tests/test_latest_no_results_regressions.py -q
.venv\Scripts\python.exe -m pytest tests/solutions/ tests/hypotheses/ -q  # بعد إعادة توجيه imports
```

### اختبارات CLI بعد التنظيف
```powershell
.venv\Scripts\python.exe -m pytest tests/cli/ -q
```
- test_registry: الأوامر المتوقعة أربعة
- test_summary: لا يذكر match-products
- test_run_logging_e2e: لا حالة match-products-help

### اختبارات UI بعد الحذف
```powershell
.venv\Scripts\python.exe -m pytest tests/ui/ -q
```
- test_streamlit_product_matching.py محذوف بالكامل

## 4. فحوصات رgression ضد القائمة الحمراء

بعد Task 4 (حذف المحرك)، شغّل:

```powershell
rg -n "from src\.core\.matching|from \.\.matching" src/tawreed/ | Measure-Object -Line
```
Expected: نفس العدد قبل التعديل (لم يُكسر شيء في tawreed).

```powershell
rg -n "matching_risk|matching_confidence|search_query_templates" src/tawreed/ src/cli/commands/cli_order.py
```
Expected: المراجع كما كانت — الملفات موجودة وتعمل.

## 5. بروتوكول التوقف

توقف فورًا وأعد التقييم لو:
- ❌ أي اختبار في `tests/core/matching/` فشل
- ❌ `order --help` تغير سلوكه
- ❌ config.yaml توقف عن التحليل (MatchingConfig)
- ❌ Streamlit crash عند الإقلاع

في هذه الحالة: راجع 05-rollback-cleanup.md §2 (التراجع لآخر commit أخضر).
