# 05 — خطة الاختبار الكاملة والنتائج (Test Plan & Results)

> الهدف المعلن: "عندما أنفذ أي حل أشغّل هذه الاختبارات — لو نجحت يبقى المشكلة اتحلت والا لم تحل".

---

## 1. إعداد بيئة الاختبار

| الخطوة | التفاصيل |
|---|---|
| المفسّر | `.venv\Scripts\python.exe` (Python 3.11.15) |
| تثبيت pytest | `.venv` كان ينقصه → `pip install pytest rapidfuzz` (9.1.1 / 3.14.5) |
| التجميع الأولي | 693 اختباراً قابل للتجميع قبل أي تعديل |

---

## 2. طبقات الاختبار (Test Pyramid)

### الطبقة 1 — Reproduction (إثبات المشكلة)
**الملف:** `tests/reproduction/test_reproduction_auto_matched_never_saved.py`

| الاختبار | يثبت ماذا | قبل الإصلاح | بعد الإصلاح |
|---|---|---|---|
| `test_perfect_match_only_run_saves_auto_matched_row` | تطابق مثالي + فلاغ مفعّل = صف `auto_matched` واحد | ❌ FAIL (`store contains: []`) | ✅ PASS |
| `test_truthiness_of_tuple_contract_is_always_true` | عقد الدالة tuple و truthiness دائماً True (جذر السبب) | ✅ PASS | ✅ PASS (توثيقي) |

### الطبقة 2 — Hypotheses (تشخيص السبب + حرسات انحدار)
**المجلد:** `tests/hypotheses/automatched/` — 6 ملفات (H1..H6) + عدّاء `run_all.py`

قبل الإصلاح: H1 CONFIRMED (score 95) = السبب الجذري.
بعد الإصلاح: H1 rejected = الخطأ لم يعد؛ H2..H6 حرسات سلوك.

```powershell
.venv\Scripts\python.exe tests\hypotheses\automatched\run_all.py
```

### الطبقة 3 — Solutions (مقارنة الحلول)
**الملف:** `tests/solutions/test_solution_comparison_automatched.py` — 8 اختبارات، 3 حلول × 5 معايير مرجّحة → **S2 = 36/36** (تفصيل في 03).

### الطبقة 4 — Post-fix E2E (شامل ما بعد الإصلاح)
**الملف:** `tests/reproduction/test_postfix_auto_matched_saving.py`

| # | السيناريو | المتوقع | النتيجة |
|---|---|---|---|
| 1 | تطابق سليم → حفظ | صف `auto_matched` بـ SP-999 | ✅ |
| 2 | رفض تضارب صريح في diagnostics | لا حفظ (حماية) | ✅ |
| 3 | `enable_manufacturer_check=True` + تضارب اسمي | لا حفظ (opt-in يعمل) | ✅ |
| 4 | يوجد `approved_match` بشري سابق | يبقى قرار البشر بلا كدس | ✅ |
| 5 | score=999 + "Approved by saved manual review" | لا إعادة حفظ | ✅ |
| 6 | status = no-results | مسار مراجعة، لا حفظ تلقائي | ✅ |
| 7 | `enable_auto_save_verified_match=False` | صفر صفوف | ✅ |

> **ملاحظة تصحيحية موثقة:** النسخة الأولى من test_5 كانت خاطئة (مرّرت score=999 بدون final_reason المطابق)؛ الحارس يتطلب **الشرطين معاً** حسب التصميم. صُحّح الاختبار (وليس الكود) ليعكس العقد الحقيقي.

### الطبقة 5 — الحزمة الكاملة (Regression)

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```

---

## 3. النتائج النهائية

### 3.1 ملفات هذا التحقيق (الجديدة)
```
tests/reproduction/ tests/solutions/ tests/hypotheses/
→ 49 passed, 6 subtests passed (0 failed)
→ استقرارية: 3 تشغيلات متتالية متطابقة
```

### 3.2 الحزمة الكاملة بعد الإصلاح
```
8 failed, 682 passed, 20 skipped, 137 subtests passed
```

### 3.3 الـ baseline (قبل أي تغيير — git stash ثم تشغيل)
```
8 failed, 680 passed, 20 skipped, 137 subtests passed
```

### 3.4 الإخفاقات الثمانية الموروثة (ليست من تغييراتنا)

| الاختبار | الطبيعة |
|---|---|
| `tests/cli/commands/test_cli_commands.py::test_load_order_items_rejects_prevented_file_as_order_excel` | CLI منفصل |
| `...::test_strict_api_match_only_failure_exits_without_traceback` | CLI منفصل |
| `...::test_strict_api_order_failure_exits_without_traceback` | CLI منفصل |
| `tests/cli/test_logging_quiet_e2e.py::test_log_level_unknown_choice_rejected` | logging e2e |
| `tests/cli/test_run_logging_e2e.py::test_help_commands_only_emit_root_records` | logging e2e |
| `tests/core/matching/test_matching_logging.py::test_async_matching_logging_...` | logging async |
| `tests/core/test_logging_audit.py::test_no_print_calls_in_src` | تدقيق source |
| `tests/tawreed/order/test_tawreed_cart_removal.py::test_remove_matching_cart_rows_...` | cart UI |

**إثبات الاستقلالية:** `git stash` (إخفاء كل تغييراتنا) → نفس الـ 8 تفشل → `git stash pop`. هذه إخفاقات بيئة/فرع موروثة من قبل (الفرع `logging_system` نشِط بتغييرات logging).

### 3.5 الاختبارات المرتبطة بمسارنا — كلها ناجحة

| حزمة اختبارات ذات صلة | النتيجة |
|---|---|
| `tests/tawreed/order/` (ما عدا cart_removal الموروث) | ✅ |
| `tests/core/manual_review/` و `tests/ui/manual_review/` | ✅ |
| `tests/ui/views/test_streamlit_product_matching.py` | ✅ |
| `tests/tawreed/api/test_tawreed_api_execution_mode.py` | ✅ |

---

## 4. التحقق من قاعدة البيانات الفعلية بعد الإصلاح (للمستخدم)

```powershell
# تشغيل حقيقي ثم فحص:
.venv\Scripts\python.exe run.py order --profile wardany --excel data/input/order.xlsx --match-only
# ثم:
.venv\Scripts\python.exe -c "import sqlite3; con=sqlite3.connect(r'state\manual_review_decisions.db'); cur=con.cursor(); cur.execute(\"SELECT manual_decision, COUNT(*) FROM manual_review_decisions GROUP BY 1\"); print(cur.fetchall())"
```
المتوقع: صفوف `auto_matched` جديدة بـ `run_id` يختلف عن `csv_import` (بصيغة طابع زمني للتشغيل).

## 5. أوامر التحقق المرجعية

```powershell
# 1) إثبات الإصلاح (الأهم)
.venv\Scripts\python.exe -m pytest tests/reproduction/ -v

# 2) حرسات الفرضيات
.venv\Scripts\python.exe tests\hypotheses\automatched\run_all.py

# 3) مقارنة الحلول (توثيقي)
.venv\Scripts\python.exe -m pytest tests/solutions/ -v

# 4) كل شيء
.venv\Scripts\python.exe -m pytest tests/ -q
```

**معيار النجاح المُعلن:** نجاح الطبقات 1+4 + عدم زيادة إخفاقات الحزمة عن baseline (8). **تحقق كل ذلك.**
