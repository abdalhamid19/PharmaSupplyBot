# 00 — التقرير الرئيسي: مشكلة عدم حفظ `auto_matched` في Saved Corrections

> **الحالة: تم حل المشكلة ✅** — التاريخ: 2026-08-30 — الفرع: `logging_system`

---

## 1. ملخص تنفيذي (Executive Summary)

| البند | التفاصيل |
|---|---|
| **المشكلة المُبلَّغة** | عند تشغيل `order run --match-only`، الأصناف لا تُحفظ في قاعدة البيانات (Saved Corrections / Manual Review Store) بصيغة `auto_matched`، بينما الحفظ بصيغة `approved_match` (عند التصحيح اليدوي) يعمل. |
| **نتيجة التحقق** | **الادعاء صحيح 100%** — تم إثباته باختبار إعادة إنتاج (Reproduction Test) وفحص قاعدة البيانات الفعلية. |
| **السبب الجذري (H1)** | سطر برمجي يعامل **tuple كـ boolean**: `if should_skip_auto_save_verified_match(...):` — الدالة تُرجع `(bool, str)` وأي tuple غير فارغ يُقيَّم كـ `True` دائماً، فيعود الحفظ التلقائي مبكراً **في كل مرة**، فلا يُكتب أي صف `auto_matched` أبداً. |
| **سبب ثانوي مُكتشَف (H1b)** | مُستخرج الشركة المصنّعة `extract_manufacturer_from_name()` معطوب — يعتبر آخر كلمة في اسم الدواء "شركة مصنّعة" (مثل `EXTRA` من `PANADOL EXTRA`)، مما يسبب تضارباً وهمياً مع `companyName` الحقيقي ويمنع الحفظ حتى بعد إصلاح الـ tuple. القياس على 1232 اسم حقيقي: **اختلاق شركة في 99% من الحالات**. |
| **الحل المُطبَّق (S2)** | 1) فك الـ tuple واستخدام القيمة المنطقية فقط. 2) ربط فحص الشركة المصنّعة بفلاغ `enable_manufacturer_check` (افتراضياً معطّل). 3) تمرير سبب الرفض الحقيقي من `diagnostics`. 4) تسجيل سبب التخطي في الـ log بدل الفشل الصامت. |
| **إصلاحان إضافيان** | (أ) **مهلة الملاحة**: `resilient_goto()` بحد أدنى 60s + إعادة محاولة واحدة — كان ركود شبكة عابر (21s) ينهي التشغيل كاملاً ([07](07_navigation_timeout_fix.md)). (ب) **هوية الشركة المصنّعة**: عقد "تعرُّف لا تخمين" — `companyName` الصريح فقط وقائمة شركات مُنسَّقة ([08](08_manufacturer_identity_fix.md)). |
| **الاختبارات** | 39 اختباراً جديداً (Reproduction 15 + Hypotheses 16 + Solutions 8) + 17 لهوية الشركة المصنّعة — كلها ناجحة. الحزمة الكاملة: **802 ناجح**، والإخفاقات الثمانية متطابقة تماماً مع baseline قبل التغيير (أُثبت بـ `git stash` + `Compare-Object`). |

---

## 2. إثبات الادعاء بالبيانات الفعلية

### 2.1 فحص قاعدة البيانات الحقيقية (`state/manual_review_decisions.db`)

```
manual_decision | count | last_updated
approved_match  | 280   | 2026-07-21 09:13:10
auto_matched    | 938   | 2026-07-20 07:24:31   ← توقفت عن النمو هنا
needs_correction| 4     | 2026-07-20 07:53:20
not_matching    | 1     | 2026-07-20 07:24:31
```

### 2.2 مصدر صفوف `auto_matched` "الأخيرة"

فحص `run_id` للصفوف الأخيرة:

```
('45413', 'ABIMOL EXTRA 20 TAB.', 'csv_import', ...)   ← كلها csv_import!
('85839', 'ACHTENON 30 TABS',     'csv_import', ...)
...
```

**كل صفوف `auto_matched` (938) جاءت من استيراد CSV قديم (`run_id = 'csv_import'`) وليس من أي تشغيل match-only فعلي.** هذا يطابق تاريخ إدخال الخطأ (commit `3d3191c` بتاريخ 2026-07-05 «ora_problem _fix»).

### 2.3 الـ commit المُدخِل للخطأ

```diff
# commit 3d3191c — src/tawreed/order/tawreed_order_summary_build.py
+    # Safety check: skip saving matches that have validation issues
+    from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
+    if should_skip_auto_save_verified_match(item, match.data, getattr(decision, 'rejection_reason', None)):
+        return
```

سطر الحماية المقصود منه منع حفظ التطابقات المتضاربة — لكنه بسبب معاملة الـ tuple كـ boolean منع **كل** الحفظ.

---

## 3. خريطة تدفق البيانات (Data Flow)

```
order --match-only  (CLI أو Streamlit)
        │
        ▼
bot.match_items_only(items)
        │
        ▼
record_match_only_success(item)  ← API: tawreed_api_flow_main.py:32
        │
        ▼
append_order_item_artifacts(profile, item, summary, decision, config)
        │                                tawreed_order_summary_build.py:16
        ▼
_handle_manual_review_or_auto_save(...)               :35
        │
        ├── manual_review_required() == True  →  append_manual_review_artifacts()
        │       (CSV للمراجعة البشرية — يعمل صح)
        │
        └── else if enable_auto_save_verified_match (افتراضي True)
                │
                ▼
        _auto_save_verified_match(item, decision)    :48
                │
                ▼
        ❌ if should_skip_auto_save_verified_match(...):   ← (True, "...") دائماً
                return   ══► الخروج المبكر الدائم — لا حفظ أبداً
                │
                ▼ (غير قابل للوصول قبل الإصلاح)
        ManualReviewStore.upsert(auto_matched)  ══► كان يُكتب هنا
```

---

## 4. لماذا `approved_match` يعمل و `auto_matched` لا يعمل؟

| المسار | نقطة الحفظ | هل يمر بالحارس المعطوب؟ | النتيجة |
|---|---|---|---|
| تصحيح بشري (UI) | Streamlit → `store.upsert(approved_match)` مباشرة | ❌ لا يمر | ✅ يعمل |
| استيراد CSV | `tools/import_csv_to_sqlite.py` → upsert مباشرة | ❌ لا يمر | ✅ يعمل |
| حفظ تلقائي بعد match | `_auto_save_verified_match` → حارس الـ tuple | ✅ يمر | ❌ معطّل |

---

## 5. الملفات المُعدَّلة

### 5.1 إصلاح `auto_matched` (المشكلة الأصلية)

| الملف | التغيير |
|---|---|
| `src/tawreed/order/tawreed_order_summary_build.py` | فك الـ tuple، استخراج `rejection_reason` من diagnostics، تمرير `matching_config`، إضافة logging للتخطي |
| `src/core/manual_review/manual_review_helpers.py` | `should_skip_auto_save()` — فحص الشركة المصنّعة أصبح opt-in عبر `enable_manufacturer_check=False` |
| `src/core/manual_review/manual_review_runtime.py` | الـ wrapper يمرر الفلاغ الجديد |

### 5.2 إصلاح انهيار مهلة الملاحة (مُكتشَف أثناء التحقق الميداني)

| الملف | التغيير |
|---|---|
| `src/tawreed/auth/tawreed_session.py` | `resilient_goto()` جديدة: حد أدنى 60s للملاحة + إعادة محاولة واحدة عند المهلة؛ استُخدمت في `open_auth_page` و `validate_saved_session` |
| `src/tawreed/cart/tawreed_cart_flow.py` | استبدال `page.goto` بـ `resilient_goto` (صفحتا السلة والطلب) |
| `src/tawreed/order/tawreed_order_processing.py` | استبدال `page.goto` بـ `resilient_goto` |
| `state/config.yaml` + `config.example.yaml` | `timeout_ms: 15000` → `45000` (مطابقة لافتراضي الكود) |

### 5.3 الإصلاح البنيوي لهوية الشركة المصنّعة (السبب المساعد H1b)

| الملف | التغيير |
|---|---|
| `src/core/identity/manufacturer_identity.py` | **تعرُّف لا تخمين**: جانب الصنف يتعرّف على `KNOWN_MANUFACTURERS` فقط (مع أولوية للأقواس)؛ جانب المرشح يعتمد على `companyName`/`supplierName` الصريح فقط بلا ارتداد لتخمين من الاسم |

القياس على 1232 اسم صنف حقيقي: الخوارزمية القديمة اختلقت شركة في **99%** من الحالات (`EXTRA`, `SACHETS`, `ACYCLOVIR`, `U`...). التفاصيل: [08_manufacturer_identity_fix.md](08_manufacturer_identity_fix.md).

## 6. ملفات الاختبار الجديدة

| الملف | الوظيفة |
|---|---|
| `tests/reproduction/test_reproduction_auto_matched_never_saved.py` | إثبات المشكلة (يفشل قبل الإصلاح، ينجح بعده) |
| `tests/reproduction/test_postfix_auto_matched_saving.py` | 8 سيناريوهات إصلاح شاملة |
| `tests/reproduction/test_resilient_goto_navigation.py` | 5 اختبارات لمهلة الملاحة وإعادة المحاولة |
| `tests/core/identity/test_manufacturer_identity_explicit_only.py` | 17 اختباراً لعقد "تعرُّف لا تخمين" |
| `tests/hypotheses/automatched/*.py` | 6 فرضيات مع scoring |
| `tests/solutions/test_solution_comparison_automatched.py` | مقارنة 3 حلول بمعايير مرجّحة |

---

## 7. فهرس التقارير التفصيلية

| التقرير | المحتوى |
|---|---|
| [01_investigation_process.md](01_investigation_process.md) | خطوات التحقيق بالتفصيل + الأدوات المستخدمة + الاكتشافات المصاحبة |
| [02_hypothesis_scoring.md](02_hypothesis_scoring.md) | الفرضيات الست + الدرجات + إثبات كل فرضية |
| [03_solution_comparison.md](03_solution_comparison.md) | الحلول الثلاثة + المعايير المرجّحة + نتيجة المقارنة |
| [04_fix_implementation.md](04_fix_implementation.md) | الكود قبل/بعد لكل ملف + شرح سطر بسطر |
| [05_test_plan_and_results.md](05_test_plan_and_results.md) | خطة الاختبار الكاملة + النتائج قبل/بعد + baseline |
| [06_regression_risk_analysis.md](06_regression_risk_analysis.md) | تحليل مخاطر الانحدار + التوصيات المستقبلية |
| [07_navigation_timeout_fix.md](07_navigation_timeout_fix.md) | انهيار مهلة الملاحة المُكتشَف أثناء التحقق الميداني + قياسات الشبكة + الإصلاح |
| [08_manufacturer_identity_fix.md](08_manufacturer_identity_fix.md) | الإصلاح البنيوي لهوية الشركة المصنّعة: قياس 99% رفض وهمي + عقد "تعرُّف لا تخمين" |

## 8. كيفية التحقق من الإصلاح مستقبلاً

```powershell
# 1. اختبار الإصلاح الأساسي (auto_matched + مهلة الملاحة)
.venv\Scripts\python.exe -m pytest tests/reproduction/ -v

# 2. حرسات الانحدار للفرضيات
.venv\Scripts\python.exe tests\hypotheses\automatched\run_all.py

# 3. مقارنة الحلول (توثيقية)
.venv\Scripts\python.exe -m pytest tests/solutions/ -v

# 4. الحزمة الكاملة
.venv\Scripts\python.exe -m pytest tests/ -q
```

**النتائج الفعلية:** **54 passed** لملفات هذا التحقيق (reproduction + solutions + hypotheses)، و**696 passed / 8 failed** للحزمة الكاملة — الإخفاقات الثمانية موروثة من الفرع قبل هذا العمل (أُثبت بـ `git stash`).
