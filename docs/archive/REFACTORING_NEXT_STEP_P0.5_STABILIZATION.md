# الخطوة التالية في Refactoring — P0.5: تثبيت انحدار التقسيم (Stabilization)

**التاريخ:** 2026-06-28
**المرحلة:** P0.5 — تثبيت ما بعد التقسيم (Post-Split Stabilization)
**الأولوية:** 🔴🔴 حرجة جداً (تسبق كل خطط P1/P2/P3)
**الحالة:** 🔴 لم يبدأ
**المرجعيات الملزمة:** `docs/project_guidelines.md` + `docs/starting_prompt.md`

---

## 0. لماذا هذه هي الخطوة التالية بالضبط؟ (Think Before Coding)

> هذا القسم يطبّق "البروتوكول الأول: تحليل التأثير" من `starting_prompt.md`.

الخطة القديمة (`REFACTORING_DETAILED_PLAN.md` و `REFACTORING_PROGRESS.md`) تفترض حالة
أساسية خضراء: **429 اختبار ناجح + line_length = 0**. لكن **القياس الفعلي للمستودع اليوم
يكذّب هذا الافتراض تماماً**. الكوميتات الأخيرة:

```
870b42e other fix for refractoring file length
666816e fix error from refractoring
6ba97e0 refractoring file length end
```

قامت بتقسيم الملفات الضخمة (P1) فعلياً، لكنها **تركت المستودع في حالة انحدار (regression)**.
لذلك **لا يجوز** البدء بأي تقسيم جديد (P1.x / P2 / P3) قبل إعادة البوابة إلى الأخضر.

### القياس الفعلي (Baseline الحقيقي — تم قياسه بالأمر)

```bash
.venv/bin/python -m unittest discover -s tests -q
# النتيجة الفعلية: Ran 353 tests — FAILED (failures=7, errors=29)

.venv/bin/python tools/rule_audit.py ; echo $?
# النتيجة الفعلية: rule_audit_violations ... exit code = 1
```

| المؤشر | ما توثّقه الخطة القديمة | **القياس الفعلي اليوم** | الفجوة |
|--------|--------------------------|--------------------------|--------|
| الاختبارات الناجحة | 429 / 429 ✅ | **353 ran، 7 fail + 29 error** ❌ | انحدار |
| line_length | 0 ✅ | **113 مخالفة** ❌ | انحدار |
| function_lines | 41 | **110 مخالفة** | انحدار |
| file_lines | 23 | **67 مخالفة** | انحدار |
| docstring | غير مذكور | **42 مخالفة** | انحدار |
| **إجمالي مخالفات البوابة** | ~64 | **332 مخالفة (exit 1)** | 🔴 |
| `rule_audit_ok` | الهدف | **غير محقق** | 🔴 |

### السبب الجذري (Root Cause — مؤكد بالأدلة)

التقسيم حوّل الملفات الضخمة إلى **واجهات رفيعة (facades)** تعيد التصدير من وحدات جديدة:

```
ai_steps.py        = 27 سطر   (كان 1037)  → يعيد التصدير من ai_review/ai_search/ai_verify_*
trace_log.py       = 116 سطر  (كان 1046)  → يعيد التصدير من trace_log_*
verifier.py        = 80 سطر   (كان 882)   → يعيد التصدير من verifier_*
normalizer.py      = 23 سطر   (كان 1327)  → يعيد التصدير من normalizer_*
indexer.py         = 84 سطر   (كان 561)   → يعيد التصدير من indexer_*
product_matching.py= 64 سطر   (كان 1117)  → يعيد التصدير من product_matching_*
tawreed.py         = 19 سطر   (كان 976)   → يعيد التصدير من tawreed_bot_*
```

هذا **تصميم سليم** (الحفاظ على الواجهة العامة عبر facade)، لكن التنفيذ **ناقص**، مما أنتج
ثلاثة أعطال متمايزة يجب معالجتها بترتيب صارم:

1. **أعطال استيراد (29 error):** اختبارات/وحدات تستورد رموزاً لم تعد موجودة في مكانها القديم
   لأن الـ facade لم يُعد تصديرها، أو لأن الرمز أُعيدت تسميته. أمثلة مؤكدة:
   | الاستيراد المكسور | الملف الهدف | الخطأ المؤكد |
   |---|---|---|
   | `_extract_json` | `verifier.py` | `cannot import name '_extract_json'` (أُعيدت تسميته إلى `extract_json`) |
   | `_auth_headers_from_state` | `tawreed_api.py` | `cannot import name '_auth_headers_from_state'` |
   | `MAX_DETAILED_MATCH_CANDIDATES` | `tawreed_match_logs.py` | `cannot import name 'MAX_DETAILED_MATCH_CANDIDATES'` |
   | `add_and_save_prevented_item` | `streamlit_order_form.py` | `cannot import name 'add_and_save_prevented_item'` |
   | `_load_order_items` | `cli_order.py` | `cannot import name '_load_order_items'` |

2. **أعطال سلوك (7 fail):** التقسيم غيّر منطق العمل عن غير قصد (مخالف صريح لـ
   "Refactoring لا يغيّر السلوك"). أمثلة مؤكدة:
   - `test_components_match_rejects_unsafe_matches` — `components_match` صارت تقبل مطابقات
     غير آمنة (VIGOTON PLUS ≠ VIGOTON، GROWTH ADULT ≠ GROWTH KIDS، B-FRESH MINT ≠ GREEN).
   - `test_manual_review_*` — ضياع/تغيّر ترتيب الاستعلامات (CYTOTEC قبل CYTO) ومنطق القرار اليدوي.

3. **عدم تزامن البوابة (332 مخالفة):** `tools/rule_audit.py` يحتوي `BASELINE_VIOLATIONS`
   و`EXCEPTED_FILE_LENGTHS` تشير إلى **الملفات الضخمة القديمة** (مثل
   `ai_steps.py:file_lines:1037`, `trace_log.py:...`, `verifier.py:...`, `normalizer.py:...`,
   `tawreed.py:...`). بعد التقسيم لم تعد تلك الأسطر موجودة، بينما الوحدات الجديدة (66 وحدة جديدة:
   `ai_review*`, `ai_search*`, `ai_verify*`, `normalizer_*`, `indexer_*`, `trace_log_*` ...)
   تنتج مخالفات **ليست في baseline** ⇒ exit 1.

> **الخلاصة:** الخطوة التالية ليست "تقسيم ملف جديد"، بل **تثبيت الانحدار الناتج عن التقسيم**.
> هذه نقطة دخول إلزامية: بدونها كل قياسات النِّسَب في الخطة الكبيرة غير موثوقة.

---

## 1. الهدف والنطاق (No Feature Creep)

> يطبّق "البروتوكول الثاني: منع زحف الميزات" من `starting_prompt.md` ومبدأ
> "Surgical Changes — المس فقط ما يجب لمسه".

### الهدف القابل للتحقق (Verifiable Goal)
1. ✅ كل اختبارات الحزمة تُجمَّع وتُجمَع (collect) دون أخطاء استيراد.
2. ✅ صفر `errors` وصفر `failures` في `unittest`.
3. ✅ `tools/rule_audit.py` يطبع `rule_audit_ok` ويُرجع exit code = 0.
4. ✅ صفر تغيير في سلوك العمل (السلوك مُجمَّد — Behavior Frozen).

### داخل النطاق (In Scope)
- إصلاح/استكمال إعادة التصدير في ملفات الـ facade لتطابق الواجهة العامة السابقة.
- تصحيح الاختبارات التي تستورد من مسار قديم **فقط عندما يكون الرمز قد انتقل عمداً**
  (تحديث مسار الاستيراد، لا تغيير منطق الاختبار).
- إصلاح أعطال السلوك الـ7 بإرجاع المنطق الأصلي (revert السلوكي للجزء المكسور فقط).
- مزامنة `BASELINE_VIOLATIONS` و`EXCEPTED_FILE_LENGTHS` في `rule_audit.py` مع البنية الجديدة.

### خارج النطاق صراحةً (Out of Scope — ممنوع)
- ❌ أي تقسيم جديد لملفات (هذا شأن P1.x القادمة بعد الأخضر).
- ❌ أي ميزة جديدة أو تحسين أداء غير مطلوب.
- ❌ إعادة تنسيق كود مجاور سليم.
- ❌ حذف "كود ميت" قديم لم يتسبب به هذا الانحدار.
- ❌ تخفيض مخالفات function_lines/line_length الجديدة عبر تقسيم (يؤجَّل؛ تُسجَّل مؤقتاً في baseline
  وفق سياسة الأداة الحالية، أو تُصلَح فقط إن كانت رخيصة وآمنة وضمن نفس الملف الملموس).

---

## 2. الاستراتيجية العامة (ترتيب صارم لا يُخالَف)

> "الأخضر أولاً": لا ننتقل لمخالفات الجودة قبل أن تمر الاختبارات. منطق العمل أهم من عدّاد الأسطر.

```
المرحلة A (إصلاح الاستيراد)  →  المرحلة B (إصلاح السلوك)  →  المرحلة C (مزامنة البوابة)  →  المرحلة D (تحقق نهائي)
   29 error → 0                   7 fail → 0                  332 violation → ok            توثيق + map
```

**قاعدة ذهبية:** بعد كل ملف يُعدَّل، شغّل وحدة الاختبار المرتبطة بذلك الملف فقط أولاً
(تغذية راجعة سريعة)، ثم الحزمة كاملة عند نهاية كل مرحلة فرعية.

---

## 3. المرحلة A — إصلاح أعطال الاستيراد (29 error)

**الهدف:** صفر `unittest.loader._FailedTest` وصفر `ImportError`.
**النسبة من P0.5:** 0% → 45%

### A.0 — حصر دقيق للأعطال (قبل أي تعديل)

وحدات الاختبار التي تفشل في الاستيراد (8 وحدات مؤكدة):
```
test_ai_decision_conflicts
test_ai_json_repair
test_cli_commands
test_min_discount_fix
test_streamlit_manual_review
test_streamlit_order
test_tawreed_api
test_tawreed_match_logs
```
بالإضافة إلى أخطاء استيراد داخل وحدات تعمل جزئياً (`test_streamlit_remove_cart`,
`test_streamlit_results`, `test_tawreed_bot`, `test_tawreed_products_flow`,
`test_tawreed_cart_removal`, `test_tawreed_api_execution_mode`, `test_tawreed_search_logic`,
`test_streamlit_main`).

**أمر الحصر الكامل:**
```bash
.venv/bin/python -m unittest discover -s tests -q 2>&1 | grep -E "ImportError|cannot import name" 
# لكل وحدة:
.venv/bin/python -c "import tests.test_tawreed_api" 2>&1 | tail -5
```

### A.1 — منهجية القرار لكل رمز مفقود (Decision Tree)

لكل `cannot import name 'X' from 'M'`:

```
هل الرمز X موجود في وحدة جديدة بعد التقسيم؟
├─ نعم، وبنفس الاسم
│    → أضف re-export في الـ facade M:  from .new_module import X   (أو __all__)
│    → السبب: الحفاظ على الواجهة العامة (project_guidelines: "Preserve existing public interfaces")
├─ نعم، لكن باسم جديد (مثل _extract_json → extract_json)
│    → القرار المفضّل: أضف alias في الـ facade للحفاظ على التوافق:
│         extract_json = ...        # في الوحدة الجديدة
│         _extract_json = extract_json   # في facade verifier.py (توافق خلفي)
│    → البديل (إن كان الرمز خاصاً private بـ "_" ومستخدماً فقط في الاختبار):
│         حدّث الاختبار ليستورد الاسم الجديد extract_json (لا تغيّر منطق الاختبار)
└─ لا، الرمز اختفى فعلياً (حُذف بالخطأ أثناء التقسيم)
     → استرجع تعريفه من git history للملف الأصلي وأعد وضعه في الوحدة المنطقية المناسبة
        git show 6ba97e0~1:src/path/old_file.py | less   # لاستخراج التعريف الأصلي
```

> **مبدأ حاسم:** الرموز الخاصة (`_name`) المستخدمة في الاختبارات تمثّل عقد اختبار قائماً.
> الأفضل **استعادة الاسم القديم كـ alias** بدل تعديل عشرات الاختبارات، إلا إذا كان alias واحد
> غير كافٍ. هذا يقلّل سطح التغيير ويحفظ "السلوك مُجمَّد".

### A.2 — جدول الإصلاحات المؤكدة (ابدأ بها)

| # | الرمز | الملف الهدف (facade) | الإجراء المقترح | وحدة التحقق |
|---|------|----------------------|------------------|-------------|
| 1 | `_extract_json` | `src/core/drug_matching/verifier.py` | alias: `_extract_json = extract_json` | `test_ai_json_repair` |
| 2 | `_auth_headers_from_state` | `src/tawreed/tawreed_api.py` | re-export/alias من الوحدة الجديدة | `test_tawreed_api` |
| 3 | `MAX_DETAILED_MATCH_CANDIDATES` | `src/tawreed/tawreed_match_logs.py` | re-export الثابت من وحدته الجديدة | `test_tawreed_match_logs` |
| 4 | `add_and_save_prevented_item` | `src/ui/streamlit_order_form.py` | re-export من `streamlit_prevented_items.py` | `test_streamlit_order` |
| 5 | `_load_order_items` | `src/cli/cli_order.py` | re-export/alias من `cli_order_items_*` | `test_cli_commands` |
| 6 | (بقية الرموز من `test_ai_decision_conflicts`, `test_min_discount_fix`, `test_streamlit_manual_review`) | حسب رسالة الخطأ | نفس شجرة القرار A.1 | الوحدة المعنية |

**خطوات تنفيذية مرتبة (الأسهل ↔ الأقل خطراً أولاً):**

- **A.2.1** `verifier.py` ← أضف `_extract_json = extract_json` (سطر واحد).
  تحقق: `.venv/bin/python -m unittest tests.test_ai_json_repair -q`
- **A.2.2** `tawreed_api.py` ← re-export `_auth_headers_from_state`.
  تحقق: `tests.test_tawreed_api`
- **A.2.3** `tawreed_match_logs.py` ← re-export `MAX_DETAILED_MATCH_CANDIDATES`.
  تحقق: `tests.test_tawreed_match_logs`
- **A.2.4** `streamlit_order_form.py` ← re-export `add_and_save_prevented_item`.
  تحقق: `tests.test_streamlit_order`
- **A.2.5** `cli_order.py` ← re-export/alias `_load_order_items`.
  تحقق: `tests.test_cli_commands`
- **A.2.6** كرّر شجرة A.1 لبقية الرموز حتى يختفي كل `_FailedTest`.

### A.3 — معيار نجاح المرحلة A
```bash
.venv/bin/python -m unittest discover -s tests -q 2>&1 | grep -c "_FailedTest"
# يجب: 0
.venv/bin/python -m unittest discover -s tests -q 2>&1 | tail -3
# يجب أن يرتفع عدد الاختبارات المُجمَّعة من 353 نحو 429، مع بقاء failures السلوكية للمرحلة B
```

---

## 4. المرحلة B — إصلاح أعطال السلوك (7 fail)

**الهدف:** صفر `failures`. **النسبة من P0.5:** 45% → 75%
**المبدأ الحاكم:** "Be terrified of changing behavior" — هذه الأعطال انحدار سلوكي حقيقي يجب
**عكسه**، لا تكييف الاختبار معه.

### B.0 — قائمة الأعطال المؤكدة

| # | الاختبار | الملف المسؤول (مرجَّح) | العَرَض المؤكد |
|---|----------|------------------------|----------------|
| 1 | `test_components_match_rejects_unsafe_matches` | `normalizer_matching_core.py` / `normalizer_matching_*` | `components_match` تقبل: VIGOTON PLUS↔VIGOTON، GROWTH ADULT↔KIDS، B-FRESH MINT↔GREEN |
| 2 | `test_manual_review_match_returns_saved_store_product_id` | `manual_review_runtime.py` | لا يُرجِع store_product_id المحفوظ |
| 3 | `test_manual_review_queries_prepend_saved_correct_query` | `manual_review_runtime.py` | ترتيب الاستعلامات: `['CYTO']` بدل `['CYTOTEC','CYTO']` |
| 4 | `test_not_matching_decision_filters_rejected_candidate` | `manual_review_runtime.py` | لا يُصفّي المرشّح المرفوض |
| 5 | `test_saved_manual_decision_turns_previous_no_match_into_match` | `manual_review_runtime.py` | القرار اليدوي المحفوظ لا يحوّل no-match إلى match |
| 6–7 | (بقية فشل `manual_review` / `tawreed_*` الظاهرة بعد المرحلة A) | حسب التتبّع | تُحصر بعد A لأن بعضها قد يكون مخفياً خلف import error |

> **تنبيه:** بعض الـ7 قد تكون أعراضاً متعدّدة لاختبار واحد بمعطيات متعددة (كـ#1 الذي يفشل
> على 3 أزواج). أعِد عدّ failures بدقة **بعد** اكتمال المرحلة A.

### B.1 — منهجية الإصلاح (Behavioral Revert)

لكل عطل سلوكي:
1. **حدّد التابع المكسور** عبر مسار الاستدعاء (semantic search على اسم التابع، مثل `components_match`).
2. **قارن مع النسخة الأصلية قبل التقسيم** للتأكد من الفرق الدلالي:
   ```bash
   git show 6ba97e0~1:src/core/drug_matching/normalizer.py > /tmp/normalizer_old.py
   # ثم قارن منطق components_match القديم بالموزّع الجديد في normalizer_matching_*
   ```
3. **أعد المنطق المفقود** إلى الوحدة الجديدة المناسبة (فرع أو شرط أو ترتيب سقط أثناء النقل).
   التركيز: شروط الرفض الآمنة (modifier mismatch مثل PLUS/ADULT/KIDS/MINT/GREEN)، وترتيب
   إضافة الاستعلامات (prepend)، وتصفية المرشّح المرفوض.
4. **لا تعدّل الاختبار** — الاختبار يمثّل السلوك الصحيح المطلوب الحفاظ عليه.

### B.2 — تركيز خاص: `components_match`
العطل يكشف أن **منطق رفض المطابقات غير الآمنة** (الذي كان في `normalizer.py` الأصلي عند
السطر ~627، تابع `components_match` بطول 111 سطراً) لم يُنقَل كاملاً إلى
`normalizer_matching_core.py` (التابع الحالي 56 سطراً). الفجوة (~55 سطراً) تحوي على الأرجح
شروط رفض المُعدِّلات (modifiers) والعلامات التجارية. **استعد هذه الشروط** من المصدر القديم.

### B.3 — معيار نجاح المرحلة B
```bash
.venv/bin/python -m unittest discover -s tests -q 2>&1 | tail -3
# يجب: Ran 429 tests ... OK   (0 failures, 0 errors)
```

---

## 5. المرحلة C — مزامنة بوابة `rule_audit.py` (332 → ok)

**الهدف:** `rule_audit_ok` + exit 0. **النسبة من P0.5:** 75% → 95%
**لا تبدأ هذه المرحلة قبل أن تكون الاختبارات 429/429 خضراء.**

### C.1 — لماذا المزامنة وليس التقسيم؟
`rule_audit.py` مصمَّم على فلسفة **baseline دَيْن مقبول**: يفشل فقط على المخالفات **الجديدة**
خارج `BASELINE_VIOLATIONS`. بعد التقسيم:
- مفاتيح baseline القديمة (للملفات الضخمة الـ7) صارت **ميتة** (الأسطر لم تعد موجودة).
- الوحدات الجديدة الـ66 تولّد مخالفات شرعية لكنها **غير مسجّلة** ⇒ exit 1.

التقسيم الإضافي لخفض هذه المخالفات هو عمل P1.x/P2 لاحق. **الآن** نُعيد تعريف الـ baseline
ليعكس الواقع، تماماً كما فعلت الأداة سابقاً مع الملفات الضخمة (دَيْن موثَّق ومقبول مؤقتاً).

### C.2 — خطوات المزامنة

- **C.2.1** نظّف `EXCEPTED_FILE_LENGTHS`: احذف الإدخالات للملفات التي لم تعد تتجاوز 100 سطر
  بعد أن صارت facades (تحقق بـ `wc -l` لكل ملف). أبقِ الاستثناءات فقط للملفات التي **ما زالت**
  تتجاوز الحد فعلاً ولها مبرر.
- **C.2.2** نظّف `BASELINE_VIOLATIONS`: احذف المفاتيح الميتة (للملفات الضخمة المقسّمة) التي لم
  تعد الأداة تنتجها.
- **C.2.3** أعد توليد baseline الحالي للمخالفات الجديدة المقبولة مؤقتاً:
  ```bash
  # عدّ المخالفات الحالية بعد خضرة الاختبارات:
  .venv/bin/python tools/rule_audit.py 2>&1 | grep ":" | grep -v rule_audit_violations > /tmp/current_violations.txt
  wc -l /tmp/current_violations.txt
  ```
  ثم أدرج الأسطر الناتجة في `BASELINE_VIOLATIONS` **بحكم هندسي**:
  - مخالفة `file_lines` لملف صار < 100: لا تُدرَج (اختفت تلقائياً).
  - مخالفة في وحدة جديدة رخيصة الإصلاح وآمنة وداخل نفس الملف: أصلِحها الآن بدل إدراجها
    (مثال: `line_length` تُكسَر بسطرين، أو `docstring` عام مفقود يُضاف docstring قصير صادق).
  - مخالفة `function_lines` تتطلب تقسيماً منطقياً: أدرجها في baseline (دَيْن مؤجَّل لـ P1.x).
- **C.2.4** عالِج مخالفات `docstring` (42) بحكمة: الدوال/الوحدات العامة الجديدة الناتجة عن
  التقسيم يجب أن تحمل docstring قصيراً صادقاً (مطلب صريح في `project_guidelines.md`:
  "Public functions and classes must have docstrings"). هذه إصلاحات رخيصة وآمنة — **أصلِحها**
  ولا تدرجها في baseline.

> **سياسة القرار "أصلِح الآن أم أجِّل":**
> | نوع المخالفة | القرار الافتراضي |
> |---|---|
> | `docstring` عام مفقود | أصلِح الآن (docstring قصير صادق) |
> | `line_length` يُحل بكسر سطرين دون تشويه | أصلِح الآن |
> | `function_lines` يحتاج استخراج helper | أجِّل (baseline) → P1.x |
> | `file_lines` لملف ما زال ضخماً منطقياً | استثنِ في EXCEPTED أو أجِّل (baseline) |

### C.3 — معيار نجاح المرحلة C
```bash
.venv/bin/python tools/rule_audit.py ; echo "exit=$?"
# يجب: rule_audit_ok   exit=0
# (يُسمح بسطر baseline_violations_remaining:N — هذا دَيْن موثَّق مقبول)
```

---

## 6. المرحلة D — التحقق النهائي والمزامنة الوثائقية

**النسبة من P0.5:** 95% → 100%

### D.1 — البوابة المزدوجة (يجب أن تمر معاً)
```bash
.venv/bin/python -m unittest discover -s tests -q     # Ran 429 tests ... OK
.venv/bin/python tools/rule_audit.py ; echo $?         # rule_audit_ok ; 0
```

### D.2 — تحقق دخان يدوي للمسارات الحرجة (لا اختبار آلي يغطيها)
- مطابقة دواء واحد عبر `pipeline` (تأكيد أن facades لا تكسر مسار الاستيراد فعلياً وقت التشغيل).
- استيراد `from src.tawreed.tawreed import TawreedBot` يعمل (واجهة Playwright عامة).
- استيراد رؤوس واجهات Streamlit الرئيسية دون خطأ.
```bash
.venv/bin/python -c "from src.tawreed.tawreed import TawreedBot; from src.core.drug_matching.normalizer import components_match, parse_drug; print('facades_ok')"
```

### D.3 — مزامنة الوثائق (State Sync — البروتوكول الثالث في starting_prompt)
- حدّث `REFACTORING_PROGRESS.md`: صحّح أرقام الاختبارات والمخالفات إلى القياس الفعلي، وأضف
  P0.5 كخطوة مكتملة قبل P1.x.
- حدّث `REFACTORING_DETAILED_PLAN.md`: ضع ملاحظة أن الـ baseline القديم كان غير دقيق، وأن
  P1 (التقسيم) نُفّذ فعلياً لكنه تطلّب P0.5 للتثبيت.
- حدّث `PROJECT_MAP.md`: أضف الوحدات الجديدة (66 وحدة: `normalizer_*`, `indexer_*`,
  `trace_log_*`, `ai_review*`, `ai_search*`, `ai_verify*`, `product_matching_*`, `tawreed_*_flow*`)
  وأفرغ قسم `[ORPHANS & PENDING]` مما عولج.

---

## 7. بروتوكول التنفيذ خطوة-بخطوة (نفّذ → تحقّق → زامِن)

> يطبّق "أمر الانطلاق" من `starting_prompt.md`: لكل خطوة (1. نفّذ → 2. تحقّق → 3. حدّث).

```bash
# 0) نقطة حفظ قبل البدء
git status && git add -A && git commit -m "checkpoint: before P0.5 stabilization"

# 1) المرحلة A — لكل رمز مكسور:
#    عدّل الـ facade (re-export/alias) ثم:
.venv/bin/python -m unittest tests.<الوحدة_المعنية> -q
#    عند انتهاء A:
.venv/bin/python -m unittest discover -s tests -q 2>&1 | grep -c "_FailedTest"   # = 0
git add -A && git commit -m "fix(P0.5-A): restore public re-exports after split"

# 2) المرحلة B — لكل عطل سلوكي:
#    استعد المنطق من git history ثم:
.venv/bin/python -m unittest tests.<الوحدة_المعنية> -q
#    عند انتهاء B:
.venv/bin/python -m unittest discover -s tests -q 2>&1 | tail -3   # Ran 429 ... OK
git add -A && git commit -m "fix(P0.5-B): revert behavioral regressions from split"

# 3) المرحلة C — مزامنة البوابة:
.venv/bin/python tools/rule_audit.py ; echo $?   # rule_audit_ok ; 0
git add -A && git commit -m "chore(P0.5-C): resync rule_audit baseline to split layout"

# 4) المرحلة D — تحقق نهائي + وثائق:
.venv/bin/python -m unittest discover -s tests -q && .venv/bin/python tools/rule_audit.py
git add -A && git commit -m "docs(P0.5-D): sync progress, plan, and project map"
```

> **ملاحظة بيئية:** أوامر الخطة القديمة كُتبت بصيغة Windows (`\\Scripts\\python`). البيئة الفعلية
> هنا **Linux**، فالمفسّر الصحيح هو `.venv/bin/python` (تم التحقق من نجاحه فعلياً).

---

## 8. المخاطر والتخفيف

| الخطر | الاحتمال | التخفيف |
|------|----------|---------|
| إصلاح alias يخفي رمزاً منقولاً خطأً | متوسط | تأكّد أن الوحدة الجديدة هي **مصدر الحقيقة**، والـ alias مجرد جسر توافق |
| "إصلاح" السلوك بتعديل الاختبار بدل الكود | عالي الضرر | ممنوع — الاختبار يمثّل العقد؛ أصلِح الكود واستعد المنطق من history |
| استعادة منطق components_match ناقصة | متوسط | قارن سطراً بسطر مع `git show 6ba97e0~1:.../normalizer.py` |
| baseline يخفي مخالفة جديدة حقيقية يجب إصلاحها | متوسط | طبّق جدول C.2 (docstring/line_length تُصلَح، function_lines تُؤجَّل فقط) |
| كسر import دوري بين الوحدات الجديدة | منخفض | الـ facade يستورد من الوحدات وليس العكس؛ حافظ على اتجاه التبعية للداخل |

---

## 9. معايير القبول النهائية لـ P0.5

- ✅ `Ran 429 tests ... OK` (0 failures، 0 errors).
- ✅ `rule_audit_ok` + exit 0 (مع `baseline_violations_remaining:N` موثَّق ومقبول).
- ✅ صفر تغيير سلوكي مقصود (السلوك مُجمَّد؛ ما تغيّر هو **استعادة** السلوك الأصلي فقط).
- ✅ كل الواجهات العامة القديمة قابلة للاستيراد (facades مكتملة).
- ✅ `rule_audit.py` baseline يعكس بنية ما بعد التقسيم (لا مفاتيح ميتة).
- ✅ الوثائق (PROGRESS / DETAILED_PLAN / PROJECT_MAP) متزامنة مع الواقع.

---

## 10. ما بعد P0.5 — الخطوة التالية المنطقية

بعد أن تعود البوابة خضراء فعلياً، يصبح من الآمن استئناف خطط الجودة بترتيب الأولوية على
**القياس الحقيقي** (لا أرقام الخطة القديمة):

1. **P0.6 — خفض الدَّين الجديد المؤجَّل:** معالجة مخالفات `function_lines` (110) و`file_lines`
   (67) للوحدات الجديدة عبر استخراج helpers منطقي (وليس آلياً)، بدفعات صغيرة + تحقق.
2. **P0.7 — config_factory.py:** يحوي أطول الأسطر في المستودع (190/284 حرفاً عند الأسطر 65/77)
   — إصلاح line_length عالي الأثر ومنخفض الخطر.
3. ثم استئناف خطط P2 (UI/artifacts) و P3 (تنظيف نهائي) كما في `REFACTORING_DETAILED_PLAN.md`.

> **مبدأ ختامي (project_guidelines + starting_prompt):** لا تقسيم لإرضاء رقم. كل استخراج يجب
> أن يحسّن التماسك أو القابلية للاختبار، ودون أي تغيير في السلوك.

---

**نهاية خطة P0.5 — التثبيت**
_ابدأ التنفيذ بالمرحلة A (إصلاح الاستيراد)، ولا تنتقل لمرحلة قبل تحقق معيار نجاحها._
