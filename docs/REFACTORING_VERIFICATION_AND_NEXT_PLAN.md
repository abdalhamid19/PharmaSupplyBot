# تقرير التحقق من إعادة الهيكلة + خطة الإصلاح والخطوة القادمة

> **النوع:** تقرير تحقق مستقل (Independent Verification) + خطة موحَّدة واحدة.
> **التاريخ:** 2026-06-29
> **الفرع:** `main` — HEAD `9e3a66e` — الشجرة نظيفة.
> **المرجع المُتحقَّق منه:** `docs/REFACTORING_PROGRESS_REPORT.md`.
> **أدوات التحقق المُستخدمة:** `git`, `python3 tools/rule_audit.py`,
> `python3 tools/run_unit_tests.py`, `python3 -m pytest`, `grep`, `wc`.

---

## 0. الحكم النهائي (Bottom Line)

**المهمة لم تكتمل، ويوجد تخريب سلوكي حقيقي (Regression) يخالف قاعدة «السلوك
مُجمَّد».** التوحيد الهيكلي تقدّم فعلاً (434 → 256 ملفاً)، لكن تقرير التقدم
`REFACTORING_PROGRESS_REPORT.md` **يحتوي على ادعاءات غير صحيحة** خفّفت من خطورة
الوضع. أبرز ما تم إثباته بالأدلة:

| الادعاء في التقرير | الواقع المُتحقَّق | الحكم |
|---|---|---|
| «3 failures موجودة مسبقاً وغير مرتبطة بالتغييرات» | كانت **0 fail** قبل دمج P1.3 مباشرةً، وأصبحت **3 fail** بعده | ❌ **كاذب — Regression حقيقي** |
| «407 passed, 0 errors» | الواقع: **305 tests, 3 failed, 33 errors** | ❌ غير دقيق |
| «P0.3: Playwright لم يَعُد يُستورد على مستوى الوحدة» | **10 ملفات** ما زالت تستورده على مستوى الوحدة | ❌ غير مكتمل |
| «11 ملف كبير فقط (>150 سطر)» | الواقع: **~44 ملفاً** أكبر من 150 سطراً | ❌ غير دقيق |
| «كسر حلقة core↔tawreed» | grep يؤكد **صفر** استيراد `..tawreed` في core | ✅ **صحيح** |
| «rule_audit_ok» | صحيح، لكن مع **342 مخالفة** حُوِّلت إلى baseline | ⚠️ صحيح شكلاً |

**الخلاصة:** يلزم **إصلاح فوري لـRegression المطابقة** قبل أي عمل آخر، ثم
إكمال المهام الناقصة (P0.3، P1.7، تقسيم الملفات الكبيرة، تنظيف baseline).

---

## 1. منهجية التحقق (Evidence Method)

تم التحقق المستقل لا الاعتماد على التقرير. الأوامر الفعلية ونتائجها:

- `python3 tools/rule_audit.py` ⇒ `rule_audit_ok` + `baseline_violations_remaining:342`.
- `grep -rn "from \.\.tawreed" src/core/` ⇒ صفر نتيجة (الحلقة مكسورة فعلاً).
- `grep -rn "^from playwright" src/` ⇒ **10 ملفات** في `tawreed`.
- `python3 tools/run_unit_tests.py` ⇒ `Ran 305 tests ... failures=3, errors=33, skipped=1`.
- تصنيف الأخطاء الـ33: **26 = playwright مفقود، 7 = dotenv مفقود** (بيئية بحتة).
- **اختبار الانحدار القاطع:** `git checkout c892ce3` (أب دمج P1.3 `86ff749`)
  ثم `pytest tests/test_product_matching.py` ⇒ **24 passed, 0 failed**.
  العودة إلى `main` ⇒ **3 failed**. ⟸ الدليل القاطع على أن P1.3 هو السبب.
- `git show 86ff749 --stat` ⇒ `product_matching_acceptance.py +408`،
  `product_matching_scoring.py +328` ⟸ الدمج **غيّر المنطق** ولم يكن نقلاً نقياً.

---

## 2. حالة كل مرحلة (Verified Status Per Phase)

| المرحلة | الادعاء | الحالة المُتحقَّقة | الدليل |
|---|---|---|---|
| P0.1 baseline | ✅ | ✅ موثّق | git history |
| P0.2 كسر حلقة core↔tawreed | ✅ | ✅ **مكتمل فعلاً** | grep = 0 |
| P0.3 إزالة تسريب Playwright | ✅ | ❌ **ملف واحد فقط من ~11** | grep يظهر 10 ملفات |
| P0.4 توحيد مصدر الإدخال | ✅ | ⚠️ موثّق فقط (لم يُحذف `input/`) | تقرير |
| P1.1 ai_rotation_config (11→1) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.2 ai_rotation (5→1) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.3 product_matching (14→4) | ✅ | ❌ **كسر السلوك (3 اختبارات)** | اختبار الانحدار |
| P1.4 matching_* (3→2) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.5 manual_review_store (2→1) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.6 order_ai_* (15→3) | ✅ | ✅ مكتمل (الحجم كبير) | order_run_artifact_rows.py=269 |
| P1.8 prevented/excel/pipeline | ✅ | ✅ مكتمل (لكن pipeline.py=434) | wc -l |
| P1.7 indexer_* (8→2) | ✅ جزئي | ⚠️ جزئي (indexer_detailed.py=464) | wc -l |
| **P1.7 trace_log_*+verifier_*** | ⏸️ مؤجل | ❌ **لم يُنفَّذ** (20+38 ملفاً) | find |
| P2.1–P2.5 tawreed | ✅ | ⚠️ جزئي (ملفات ضخمة متبقية) | tawreed_product_export.py=588 |
| P3.1–P3.4 cli+ui | ✅ | ⚠️ جزئي (cli_parser.py=475, streamlit_order.py=561) | wc -l |
| P4.1–P4.4 تنظيف | ✅ | ✅ مكتمل | git, docs/archive |

---

## 3. المشكلات المكتشفة (Discovered Issues) — مرتبة بالخطورة

### 🔴 خطر حرج (Critical — يخالف «السلوك مُجمَّد»)

**ISSUE-1: Regression في منطق مطابقة المنتجات (أدخله P1.3).**
- 3 اختبارات كانت تنجح قبل P1.3 وتفشل الآن:
  1. `test_arabic_variant_guard_rejects_wrong_bebelac_ar_row`
     ⟸ حارس المتغير العربي (Arabic variant guard) تعطّل.
  2. `test_duplicate_candidate_across_queries_is_scored_once`
     ⟸ المرشح المكرر يُحتسب مرتين (`diagnostics 2 != 1`).
  3. `test_unrequested_advanced_variant_loses_to_plain_polyfresh`
     ⟸ `decision.best_match` يعود `None` بدل المطابقة الصحيحة.
- **الخطورة:** هذه حراسات سلامة في اختيار الدواء (حجم/متغير/تكرار). تغييرها
  يعني سلوك طلب خاطئ محتمل في الإنتاج — أخطر من أي مخالفة تنسيق.
- **الملفات المتورطة:** `src/core/product_matching_acceptance.py` (+408 سطر في
  الدمج)، `src/core/product_matching_scoring.py` (+328)،
  `src/core/product_matching_decisions.py`.

### 🟠 خطر عالٍ (High)

**ISSUE-2: P0.3 غير مكتمل — Playwright يُستورد على مستوى الوحدة في 10 ملفات.**
- الملفات: `tawreed_headless_auth_refresh.py:6`, `tawreed_artifacts.py:6`,
  `tawreed_search_logic.py:8`, `tawreed.py:11`, `tawreed_checkout.py:4`,
  `tawreed_product_export.py:13`, `tawreed_timing.py:5`,
  `tawreed_navigation.py:5`, `tawreed_order_processing.py:5`,
  `tawreed_cart_removal.py:8`.
- **الأثر:** 26 اختباراً يفشل في الجمع عند غياب playwright؛ طبقة integration
  تُحمَّل قسراً. التقرير ادّعى الحل بينما حُلّ ملف واحد فقط.

**ISSUE-3: بيئة الاختبار ناقصة (playwright + python-dotenv غير مثبتين).**
- 33 خطأ جمع = 26 playwright + 7 dotenv. بيئة لا كود، لكنها تمنع التحقق الكامل
  من «لا Regression» في طبقتي tawreed/cli.

### 🟡 خطر متوسط (Medium)

**ISSUE-4: التوحيد غير مكتمل — ~44 ملفاً أكبر من 150 سطراً.**
- أكبرها: `tawreed_product_export.py`=588, `streamlit_order.py`=561,
  `tawreed_order_flow.py`=515, `cli_parser.py`=475, `indexer_detailed.py`=464,
  `pipeline.py`=434, `tawreed_api_flow.py`=420, `tawreed_api_contract.py`=419.
- بعض الدمج تجاوز الهدف فأنتج ملفات «سمينة» جديدة (عكس الهدف).

**ISSUE-5: P1.7 (trace_log_* = 20 ملفاً، verifier_* = 38 ملفاً) لم يُنفَّذ.**
- أكبر عائلتين متبقيتين في `drug_matching`، مؤجلتان بقرار التقرير.

**ISSUE-6: 342 مخالفة حُوِّلت إلى `BASELINE_VIOLATIONS` بدل حلها.**
- `rule_audit_ok` مُضلِّل: 125 line_length + 76 file_lines + 31 docstring +
  دوال طويلة. baseline تضخّم بدل أن ينكمش.

### 🟢 خطر منخفض (Low)

**ISSUE-7: ازدواجية `input/` و `data/input/` ما زالت قائمة** (وُثّقت ولم تُحَل).
**ISSUE-8: التقرير `REFACTORING_PROGRESS_REPORT.md` يحوي أرقاماً غير دقيقة**
ويصف Regression بأنه «pre-existing» — يجب تصحيحه حتى لا يضلّل التطوير اللاحق.

---

## 4. الخطة الموحَّدة (خطة واحدة مرقّمة من الأهم للأقل أهمية)

> قاعدة حاكمة: **لا تغيير سلوك إضافي.** الإصلاح يعيد السلوك لما كان قبل P1.3.
> كل بند: المشكلة ⟸ المطلوب ⟸ معيار النجاح ⟸ بوابة التحقق.

---

### البند 1 — [حرج] إصلاح Regression منطق المطابقة (ISSUE-1)
**لماذا أولاً:** خطر سلوكي إنتاجي ويخالف «السلوك مُجمَّد».
**المطلوب خطوة بخطوة:**
1. `git show 86ff749 -- src/core/product_matching_acceptance.py
   src/core/product_matching_scoring.py src/core/product_matching_decisions.py`
   لمقارنة المنطق قبل/بعد الدمج سطراً بسطر.
2. استخراج المنطق الأصلي للملفات المصدر قبل الدمج عبر:
   `git show c892ce3:src/core/product_matching_safe_omission.py` و
   `..._identity.py` و `..._token_scoring.py` و `..._sequence_scoring.py`.
3. تحديد الفرق الدلالي الذي أسقط: (أ) حارس المتغير العربي، (ب) إزالة تكرار
   المرشحات، (ج) منطق رفض الحجم/المتغير المتقدم.
4. إعادة المنطق المفقود إلى الملفات المدمجة **دون** إعادة التفتيت.
**معيار النجاح:** الاختبارات الثلاثة تنجح:
`pytest tests/test_product_matching.py -q` ⇒ `24 passed, 0 failed`.
**بوابة التحقق:** `pytest tests/test_product_matching.py tests/test_match.py
tests/test_matching_confidence.py tests/test_matching_risk.py -q` كلها تمر.

---

### البند 2 — [عالٍ] تثبيت بيئة الاختبار الكاملة (ISSUE-3)
**لماذا:** بدونها لا يمكن إثبات عدم وجود Regression في tawreed/cli.
**المطلوب:**
1. `pip install -r requirements.txt`
2. `pip install python-dotenv` (إن لم يكن ضمن requirements، أضِفه).
3. `playwright install chromium`.
**معيار النجاح:** `python3 -m pytest --co -q` ⇒ **0 أخطاء جمع** (305 → كل
الاختبارات تُجمع، المتوقع ~432).
**بوابة التحقق:** `python3 tools/run_unit_tests.py` يعمل بلا `errors=`.

---

### البند 3 — [عالٍ] إكمال P0.3: تأجيل استيراد Playwright (ISSUE-2)
**لماذا:** فصل طبقي صحيح + الاختبارات النقية يجب ألا تنهار بغياب المتصفح.
**المطلوب:**
1. للملفات التي تستورد فقط نوع `Page`/`Response` (تلميح نوع): استخدم
   `from __future__ import annotations` + `TYPE_CHECKING` block لتفادي
   الاستيراد وقت التشغيل. الملفات: `tawreed_artifacts.py`,
   `tawreed_search_logic.py`, `tawreed_checkout.py`, `tawreed_product_export.py`,
   `tawreed_timing.py`, `tawreed_navigation.py`, `tawreed_order_processing.py`,
   `tawreed_cart_removal.py`.
2. للملفات التي تستورد `sync_playwright` (تشغيل فعلي): تأجيل داخل الدالة
   (lazy import) كما فُعِل في `tawreed_api_main.py`. الملفات:
   `tawreed.py`, `tawreed_headless_auth_refresh.py`.
**معيار النجاح:** `grep -rn "^from playwright\|^import playwright" src/` ⇒ صفر
استيراد على مستوى الوحدة خارج بلوكات `TYPE_CHECKING`.
**بوابة التحقق:** استيراد أي وحدة core/tawreed دون تثبيت playwright لا ينهار
عند الجمع.

---

### البند 4 — [متوسط] تصحيح تقرير التقدم المُضلِّل (ISSUE-8)
**لماذا:** التقرير الحالي يصف Regression كـ«pre-existing» ويضلّل أي مطوّر لاحق.
**المطلوب:** تحديث `REFACTORING_PROGRESS_REPORT.md`:
- تصحيح بند الاختبارات إلى الأرقام الفعلية (305/3 fail/33 env errors).
- تصحيح وصف الـ3 failures إلى «Regression من P1.3 — قيد الإصلاح (البند 1)».
- تصحيح عدد الملفات الكبيرة (~44 لا 11) وحالة P0.3 (ناقص).
**معيار النجاح:** التقرير يطابق المخرجات الفعلية للأدوات.

---

### البند 5 — [متوسط] تقسيم الملفات «السمينة» الناتجة عن الدمج (ISSUE-4)
**لماذا:** بعض الدمج تجاوز الهدف فأنتج ملفات >400 سطر (عكس الهدف الصحي 60–150).
**المطلوب (بترتيب الحجم، لكل ملف على حدة + commit مستقل):**
1. `tawreed_product_export.py` (588) → فصل API/collection/rows/files.
2. `streamlit_order.py` (561) → فصل form/command/process/state.
3. `tawreed_order_flow.py` (515) → فصل match/placement/delegation.
4. `cli_parser.py` (475) → مجموعتان منطقيتان (order/cart vs match/export/auth).
5. `indexer_detailed.py` (464), `pipeline.py` (434), `tawreed_api_flow.py` (420),
   `tawreed_api_contract.py` (419), `tawreed_match_logs.py` (403),
   `tawreed_order_summary.py` (377), `streamlit_manual_review.py` (374).
**قاعدة:** فصل حول حدود منطقية فقط (لا تفتيت ميكانيكي)، الإبقاء على الواجهة
العامة عبر re-export.
**معيار النجاح:** لا ملف >~250–300 سطراً بلا مبرر؛ الاختبارات المرتبطة تمر.
**بوابة التحقق:** `pytest -q` + `rule_audit.py` بعد كل تقسيم.

---

### البند 6 — [متوسط] إكمال P1.7: توحيد trace_log_* و verifier_* (ISSUE-5)
**لماذا:** أكبر عائلتين متبقيتين (20 + 38 = 58 ملفاً) في `drug_matching`.
**المطلوب:**
1. `verifier_*` (38 ملفاً) → ~4–5 وحدات: request/response/review/helpers/core.
2. `trace_log_*` (20 ملفاً) → ~4–5 وحدات حسب المرحلة (phase1/phase2/ai/output).
3. الإبقاء على الواجهة العامة وعدم تغيير أي منطق تتبّع.
**معيار النجاح:** `pytest tests/test_matching_logging.py tests/test_drug_matching_*
-q` تمر؛ عدد ملفات العائلتين ينخفض إلى ≤10.
**بوابة التحقق:** `rule_audit.py` لا يزيد المخالفات.

---

### البند 7 — [منخفض] حل ازدواجية مصدر الإدخال (ISSUE-7)
**المطلوب:** تأكيد أن الكود يستخدم `data/input/` حصراً (grep)، ثم إزالة/توحيد
`input/` بعد التأكد من خلوه أو نقل محتواه. تحديث `config.yaml` لمسار واحد.
**معيار النجاح:** مسار إدخال وحيد؛ الأوامر والاختبارات تعمل.

---

### البند 8 — [منخفض] تنظيف baseline التدقيق (ISSUE-6)
**لماذا:** `baseline_violations_remaining:342` دَين تقني مُقنَّع.
**المطلوب:** بعد البنود 5 و6، تقليص `EXCEPTED_FILE_LENGTHS` و
`BASELINE_VIOLATIONS` في `tools/rule_audit.py` لتعكس الواقع، وإصلاح المخالفات
السهلة (31 docstring مفقود، 125 سطراً طويلاً).
**معيار النجاح:** `baseline_violations_remaining` ينخفض بوضوح (هدف <150).

---

## 5. خطة الخطوة القادمة في الـRefactoring (Next Step — تنفيذ فوري)

**الخطوة التالية المُلزِمة قبل أي توحيد إضافي هي البند 1 (إصلاح Regression).**
تسلسل التنفيذ الموصى به:

1. **الآن:** البند 1 — إصلاح Regression المطابقة (إعادة السلوك لما قبل P1.3).
   - معيار التوقف: `pytest tests/test_product_matching.py` = 24 passed.
2. **ثم:** البند 2 — تثبيت البيئة، والبند 3 — إكمال P0.3 (lazy/TYPE_CHECKING).
   - معيار التوقف: `pytest --co` بصفر أخطاء جمع.
3. **ثم:** البند 4 — تصحيح تقرير التقدم ليطابق الواقع.
4. **بعد الاستقرار:** البند 5 (تقسيم الملفات السمينة) ثم البند 6 (P1.7).
5. **أخيراً:** البند 7 (الإدخال) ثم البند 8 (تنظيف baseline).

**بوابة عامة بعد كل بند:** `python3 tools/run_unit_tests.py` يجب ألا يُدخل أي
فشل جديد مقارنةً بالحالة بعد البند 1، و`rule_audit.py` يجب ألا يزيد المخالفات.

---

## 6. ما تم التحقق منه فعلياً مقابل ما يتطلب البيئة

- **مُتحقَّق محلياً (بلا playwright):** اختبارات core النقية، كسر الحلقة،
  مخالفات التدقيق، أحجام الملفات، اختبار انحدار P1.3.
- **يتطلب بيئة كاملة للتحقق النهائي (البند 2):** اختبارات `tawreed_*`,
  `cli_*`, `streamlit_*`, `item_worker_*` (محجوبة حالياً بأخطاء بيئية).
- **مخاطر متبقية بعد التحقق:** لا يمكن إثبات خلو طبقتي tawreed/cli من Regression
  حتى تُثبَّت البيئة وتُجمَع كل الاختبارات (البند 2).
