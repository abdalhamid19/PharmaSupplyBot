# تقرير تحقق مستقل + خطة موحَّدة لإكمال إعادة الهيكلة

> **النوع:** تحقق مستقل (Independent Verification) بأدلة حية + خطة واحدة موحَّدة مرقّمة بالأولوية.
> **التاريخ:** 2026-06-29
> **الفرع:** `main` — HEAD `84b77af` — الشجرة نظيفة (`git status` = clean).
> **المراجع:** `docs/REFACTORING_PROGRESS_REPORT.md` و `docs/REFACTORING_VERIFICATION_AND_NEXT_PLAN.md`.
> **أدوات التحقق:** `git`, `python3 tools/rule_audit.py`, `python3 tools/run_unit_tests.py`,
> `python3 -m pytest`, `grep`, `wc`. كل رقم أدناه مأخوذ من تنفيذ فعلي على HEAD الحالي.

---

## 0. الحكم النهائي (Bottom Line)

**المهمة لم تكتمل بالكامل، لكن لا يوجد تخريب سلوكي (Regression) في منطق المطابقة بعد الآن.**

تقدّم حقيقي تحقّق منذ آخر تقرير تحقق: تم **إصلاح Regression الـ3 اختبارات فعلاً**، وبقيت
بنية core/tawreed سليمة. لكن تقرير التقدم `REFACTORING_PROGRESS_REPORT.md` **ما زال يحتوي
على ادعاءات غير صحيحة** عن الحالة الحالية، وثلاث مهام معلنة كـ«مكتملة» لم تُنفَّذ فعلياً.

| الادعاء في تقرير التقدم | الواقع المُتحقَّق على HEAD `84b77af` | الحكم |
|---|---|---|
| «إصلاح Regression: الاختبارات الثلاثة تنجح الآن» | `pytest test_product_matching.py` ⇒ **24 passed** والثلاثة المسمّاة تنجح | ✅ **صحيح — أُصلِح فعلاً** |
| «كسر حلقة core↔tawreed» | `grep` ⇒ **صفر** استيراد `..tawreed` في core | ✅ **صحيح** |
| «إكمال P0.3: تأجيل Playwright في 10 ملفات» | لا يزال **10 ملفات** تستورد playwright على مستوى الوحدة | ❌ **غير مُنفَّذ** |
| «حل ازدواجية الإدخال: حذف `input/` الفارغ» | مجلد `input/` **ما زال موجوداً وغير فارغ** (3 مجلدات فرعية) | ❌ **غير مُنفَّذ** |
| «rule_audit_ok» | الواقع: `python3 tools/rule_audit.py` ⇒ **`rule_audit_violations`** + `EXIT=1` | ❌ **التدقيق يفشل** |
| «410 passed, 0 errors» | الواقع: `Ran 308 tests ... FAILED (errors=34, skipped=1)` | ❌ غير دقيق |
| «11 ملف كبير فقط (>150 سطر)» | الواقع: **61 ملفاً** أكبر من 150 سطراً | ❌ غير دقيق |
| «تنظيف baseline: إصلاح 125 انتهاك» | التدقيق ما زال يطبع **86 انتهاكاً حياً** ويفشل | ❌ غير دقيق |

**الخلاصة:** السلوك الآن آمن (لا Regression)، لكن المهمة **ناقصة في 5 محاور**: بوابة التدقيق
تفشل، البيئة ناقصة، P0.3 غير مكتمل، ازدواجية الإدخال قائمة، والتوحيد غير مكتمل (61 ملفاً كبيراً).

---

## 1. منهجية التحقق (Evidence Method)

تحقق مستقل لا اعتماد على التقرير. الأوامر الفعلية ونتائجها على HEAD `84b77af`:

- `python3 -m pytest tests/test_product_matching.py -q` ⇒ **`24 passed, 8 subtests passed`**.
- `pytest -k "arabic_variant_guard_rejects_wrong_bebelac or duplicate_candidate_across_queries
  or unrequested_advanced_variant"` ⇒ **`3 passed`** (الاختبارات الثلاثة المُتورّطة في Regression).
- `grep -rn "from \.\.tawreed\|from src\.tawreed" src/core/` ⇒ **صفر** (الحلقة مكسورة).
- `grep -rn "^from playwright\|^import playwright" src/` ⇒ **10 ملفات** في `tawreed`
  (`tawreed_order_placement.py:7`, `tawreed_dialogs.py:5`, `tawreed_products_flow.py:7`,
  `tawreed_ui.py:3`, `tawreed_cart_flow.py:7`, `tawreed_product_search.py:9`,
  `tawreed_order_match.py:7`, `tawreed_login_detection.py:5`, `tawreed_auth.py:10`,
  `tawreed_session.py:10`).
- `python3 tools/rule_audit.py; echo $?` ⇒ آخر سطر **`rule_audit_violations`** و **`EXIT=1`**؛
  عدد أسطر الانتهاكات الحية = **86**.
- `python3 tools/run_unit_tests.py` ⇒ **`Ran 308 tests ... FAILED (errors=34, skipped=1)`**.
  الأخطاء الـ34 = **playwright غير مثبَّت + python-dotenv غير مثبَّت** (بيئة لا كود؛
  كلاهما مُدرَج في `requirements.txt:3` و `requirements.txt:5`).
- عدّ الملفات الكبيرة: حلقة `wc -l` على `src/**/*.py` ⇒ **61 ملفاً > 150 سطراً**.
  أكبرها: `verifier_request.py`=499, `product_matching_acceptance.py`=431,
  `trace_log_ai.py`=400, `tawreed_order_summary.py`=377, `streamlit_manual_review.py`=374.
- `ls input/` ⇒ `order_items/ prevented_items/ remove_items/` (موجود وغير فارغ).
- إجمالي ملفات `src/**/*.py` الحالي = **263 ملفاً**.

**ملاحظة تصحيحية مهمة:** بوابة التدقيق كانت تفشل **أيضاً** في الـcommit السابق `9e3a66e`
(تحقّقتُ بـ`git checkout 9e3a66e -- tools/rule_audit.py`). أي أن الفشل ليس انحداراً جديداً
أدخله آخر commit، بل حالة قائمة لم تُحَل رغم ادعاء «rule_audit_ok» في التقرير.

---

## 2. حالة كل مرحلة (Verified Status Per Phase)

| المرحلة | الادعاء | الحالة المُتحقَّقة | الدليل |
|---|---|---|---|
| P0.1 baseline | ✅ | ✅ موثّق | git history |
| P0.2 كسر حلقة core↔tawreed | ✅ | ✅ **مكتمل فعلاً** | `grep` = 0 |
| P0.3 إزالة تسريب Playwright | ✅ | ❌ **غير مكتمل (10 ملفات)** | `grep` يُظهر 10 |
| P0.4 توحيد مصدر الإدخال | ✅ «حُذف input/» | ❌ **`input/` ما زال موجوداً وغير فارغ** | `ls input/` |
| P1.1 ai_rotation_config (11→1) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.2 ai_rotation (5→1) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.3 product_matching (14→4) | ✅ | ✅ **السلوك أُعيد** (لا Regression) | 24 passed |
| P1.4 matching_* (3→2) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.5 manual_review_store (2→1) | ✅ | ✅ مكتمل | الملفات محذوفة |
| P1.6 order_ai_* (15→3/4) | ✅ | ✅ مكتمل (الحجم كبير 269) | `wc -l` |
| P1.7 indexer_* | ✅ | ⚠️ جزئي (`indexer_lookup.py`=370) | `wc -l` |
| P1.7 trace_log_* + verifier_* | ✅ «مكتمل» | ⚠️ دُمج لكن أنتج ملفات ضخمة (verifier_request=499) | `wc -l` |
| P1.8 prevented/excel/pipeline | ✅ | ✅ مكتمل | git |
| P2.1–P2.5 tawreed | ✅ | ⚠️ جزئي (ملفات كبيرة متبقية) | `wc -l` |
| P3.1–P3.4 cli+ui | ✅ | ⚠️ جزئي (`cli_order.py`=355, `streamlit_manual_review.py`=374) | `wc -l` |
| P4.1–P4.3 تنظيف/أرشفة | ✅ | ✅ مكتمل | docs/archive |
| P4.4 مزامنة rule_audit | ✅ «rule_audit_ok» | ❌ **التدقيق يفشل (EXIT=1)** | تنفيذ |

---

## 3. المشكلات المكتشفة (Discovered Issues) — مرتبة بالخطورة

### 🔴 خطر حرج (Critical)
**لا يوجد Regression سلوكي حالياً.** ✅ اختبارات منطق المطابقة الـ24 كلها تنجح، والاختبارات
الثلاثة التي كانت تفشل تنجح الآن. هذا أهم بند وقد تحقّق فعلاً.

### 🟠 خطر عالٍ (High)

**ISSUE-A: بوابة التدقيق `rule_audit.py` تفشل (`rule_audit_violations`, EXIT=1).**
- التقرير يعلن `rule_audit_ok`، لكن التنفيذ الفعلي يخرج بـ**86 انتهاكاً حياً** ورمز خروج 1.
- الأثر: أي CI يربط البوابة بهذا الأمر سيفشل؛ ادعاء «نظيف» مُضلِّل.

**ISSUE-B: P0.3 غير مكتمل — Playwright يُستورد على مستوى الوحدة في 10 ملفات.**
- الملفات: `tawreed_order_placement.py`, `tawreed_dialogs.py`, `tawreed_products_flow.py`,
  `tawreed_ui.py`, `tawreed_cart_flow.py`, `tawreed_product_search.py`,
  `tawreed_order_match.py`, `tawreed_login_detection.py`, `tawreed_auth.py`,
  `tawreed_session.py`.
- الأثر: 34 خطأ جمع عند غياب المتصفح؛ يستحيل إثبات «لا Regression» في tawreed/cli محلياً.

**ISSUE-C: بيئة الاختبار ناقصة (playwright + python-dotenv غير مثبَّتين محلياً).**
- كلاهما في `requirements.txt`، لكن غير مثبَّت في البيئة الحالية ⇒ 34 خطأ جمع.
- بيئة لا كود، لكنها تحجب التحقق الكامل من طبقتي tawreed/cli/streamlit.

### 🟡 خطر متوسط (Medium)

**ISSUE-D: التوحيد غير مكتمل — 61 ملفاً > 150 سطراً (لا 11).**
- أكبرها: `verifier_request.py`=499, `product_matching_acceptance.py`=431,
  `trace_log_ai.py`=400, `tawreed_order_summary.py`=377, `streamlit_manual_review.py`=374,
  `indexer_lookup.py`=370, `trace_log_output.py`=364, `verifier_core.py`=356,
  `cli_order.py`=355, `tawreed_session.py`=339.
- بعض عمليات الدمج تجاوزت الهدف فأنتجت ملفات «سمينة» جديدة (عكس هدف 60–150 سطراً).

**ISSUE-E: ادعاءات تقرير التقدم غير دقيقة عن الحالة الحالية.**
- يصف input/ كـ«محذوف»، التدقيق كـ«ok»، الاختبارات كـ«410 passed/0 errors»،
  والملفات الكبيرة كـ«11». كلها لا تطابق التنفيذ الفعلي ⇒ يضلّل أي مطوّر لاحق.

### 🟢 خطر منخفض (Low)

**ISSUE-F: ازدواجية `input/` و `data/input/` قائمة.** `input/` موجود وغير فارغ رغم ادعاء حذفه.
الكود يستخدم `data/input/` (مؤكَّد سابقاً)، فـ`input/` بقايا يجب توحيدها/إزالتها.

---

## 4. الخطة الموحَّدة (خطة واحدة مرقّمة من الأهم للأقل أهمية)

> قاعدة حاكمة: **لا تغيير سلوك إضافي.** كل بند: المشكلة ⟸ المطلوب ⟸ معيار النجاح ⟸ بوابة التحقق.
> ترتيب البنود = ترتيب التنفيذ الموصى به.

---

### البند 1 — [عالٍ] تثبيت بيئة الاختبار الكاملة (ISSUE-C)
**لماذا أولاً:** بدونها لا يمكن إثبات عدم وجود Regression في tawreed/cli/streamlit (34 خطأ جمع).
**المطلوب:**
1. `pip install -r requirements.txt` (يتضمن playwright + python-dotenv المُدرَجين).
2. `python3 -m playwright install chromium`.
**معيار النجاح:** `python3 -m pytest --co -q` ⇒ **0 أخطاء جمع** (282 → ~313+ مُجمَّعة).
**بوابة التحقق:** `python3 tools/run_unit_tests.py` يعمل بلا `errors=` (errors=0).

---

### البند 2 — [عالٍ] إصلاح بوابة التدقيق `rule_audit.py` لتعكس الواقع (ISSUE-A)
**لماذا:** البوابة تفشل (EXIT=1) رغم ادعاء `rule_audit_ok`؛ يجب أن تكون البوابة صادقة.
**المطلوب خطوة بخطوة:**
1. `python3 tools/rule_audit.py > /tmp/audit.txt` ثم فرز الـ86 انتهاكاً الحية إلى فئات
   (`file_lines`, `function_lines`, `line_length`, `docstring`).
2. إصلاح الانتهاكات السهلة فعلياً (line_length, docstring) في الكود — لا في baseline.
3. للملفات الكبيرة التي ستُقسَّم لاحقاً (البند 4): إمّا تسجيلها صراحةً في
   `EXCEPTED_FILE_LENGTHS`/`BASELINE_VIOLATIONS` بمبرر مؤقّت، أو تقسيمها أولاً.
4. هدف نهائي: `rule_audit.py` يخرج `rule_audit_ok` و`EXIT=0`.
**معيار النجاح:** `python3 tools/rule_audit.py; echo $?` ⇒ آخر سطر `rule_audit_ok` و `0`.
**بوابة التحقق:** الأمر يُعاد تشغيله بعد كل تعديل لا يُدخل انتهاكاً جديداً.

---

### البند 3 — [عالٍ] إكمال P0.3: تأجيل استيراد Playwright في الـ10 ملفات (ISSUE-B)
**لماذا:** فصل طبقي صحيح + الاختبارات النقية يجب ألا تنهار بغياب المتصفح.
**المطلوب:**
1. للملفات التي تستورد تلميحات الأنواع فقط (`Page`, `Locator`, `Response`): أضِف
   `from __future__ import annotations` + كتلة `if TYPE_CHECKING:` للاستيراد. الملفات:
   `tawreed_dialogs.py`, `tawreed_products_flow.py`, `tawreed_ui.py`,
   `tawreed_product_search.py`, `tawreed_login_detection.py`, `tawreed_auth.py`,
   `tawreed_session.py`.
2. للملفات التي تستورد `sync_playwright` (تشغيل فعلي): تأجيل داخل الدالة (lazy import)
   كما فُعِل في `tawreed_api_main.py`. الملفات: `tawreed_order_placement.py`,
   `tawreed_cart_flow.py`, `tawreed_order_match.py`.
**معيار النجاح:** `grep -rn "^from playwright\|^import playwright" src/` ⇒ **صفر** خارج كتل
`TYPE_CHECKING`.
**بوابة التحقق:** استيراد أي وحدة tawreed دون تثبيت playwright لا ينهار عند الجمع.

---

### البند 4 — [متوسط] تقسيم الملفات «السمينة» (ISSUE-D)
**لماذا:** 61 ملفاً > 150 سطراً؛ بعض الدمج تجاوز الهدف (الهدف الصحي 60–150 سطراً).
**المطلوب (بترتيب الحجم، كل ملف commit مستقل):**
1. `src/core/drug_matching/verifier_request.py` (499) → request/build/parse/validate.
2. `src/core/product_matching_acceptance.py` (431) → identity/normalization/components/safe_omission.
3. `src/core/drug_matching/trace_log_ai.py` (400) → ai_logging/ai_records.
4. `src/tawreed/tawreed_order_summary.py` (377), `src/ui/streamlit_manual_review.py` (374),
   `src/core/drug_matching/indexer_lookup.py` (370), `trace_log_output.py` (364),
   `verifier_core.py` (356), `src/cli/cli_order.py` (355), `tawreed_session.py` (339).
**قاعدة:** فصل حول حدود منطقية فقط (لا تفتيت ميكانيكي)، الإبقاء على الواجهة العامة عبر re-export.
**معيار النجاح:** لا ملف >~300 سطراً بلا مبرر؛ الاختبارات المرتبطة تمر.
**بوابة التحقق:** `pytest -q` المرتبط + `rule_audit.py` بعد كل تقسيم لا يزيد المخالفات.

---

### البند 5 — [متوسط] تصحيح تقرير التقدم المُضلِّل (ISSUE-E)
**لماذا:** التقرير يصف input/ كمحذوف، التدقيق كـ ok، الاختبارات كـ 410/0 errors، والملفات
الكبيرة كـ 11 — كلها لا تطابق الواقع.
**المطلوب:** تحديث `REFACTORING_PROGRESS_REPORT.md`:
- تصحيح كتلة الاختبارات إلى الأرقام الفعلية (308 مُجمَّعة محلياً، 34 env error حتى البند 1).
- تصحيح حالة P0.3 إلى «ناقص — 10 ملفات» (مرتبط بالبند 3).
- تصحيح حالة input/ إلى «قائم» (مرتبط بالبند 6).
- تصحيح حالة التدقيق إلى «يفشل حتى البند 2».
- تصحيح عدد الملفات الكبيرة إلى 61.
**معيار النجاح:** كل رقم في التقرير يطابق مخرجات الأدوات الفعلية.

---

### البند 6 — [منخفض] حل ازدواجية مصدر الإدخال (ISSUE-F)
**المطلوب:**
1. تأكيد أن الكود يستخدم `data/input/` حصراً (`grep -rn "input/" src/`).
2. نقل أي محتوى مفيد من `input/order_items|prevented_items|remove_items` إلى `data/input/`
   ثم إزالة `input/` (أو تحويله إلى symlink موثّق إن لزم التوافق).
3. تثبيت مسار واحد في `config.yaml`/الكود.
**معيار النجاح:** مسار إدخال وحيد؛ الأوامر والاختبارات تعمل.

---

## 5. خطة الخطوة القادمة في الـRefactoring (Next Step — تنفيذ فوري)

السلوك آمن الآن (لا Regression)، لذا الخطوة التالية المُلزِمة هي **استعادة صدق البوابات**
ثم إكمال التوحيد. التسلسل الموصى به:

1. **الآن:** البند 1 (تثبيت البيئة) — معيار التوقف: `pytest --co` بصفر أخطاء جمع.
2. **ثم:** البند 2 (إصلاح بوابة التدقيق) — معيار التوقف: `rule_audit_ok` + EXIT=0.
3. **ثم:** البند 3 (إكمال P0.3) — معيار التوقف: صفر استيراد playwright على مستوى الوحدة.
4. **بعد استقرار البوابات:** البند 4 (تقسيم الملفات السمينة، ملفاً ملفاً بـ commit مستقل).
5. **ثم:** البند 5 (تصحيح التقرير) ثم البند 6 (توحيد الإدخال).

**بوابة عامة بعد كل بند:** `python3 tools/run_unit_tests.py` (بعد البند 1) لا يُدخل أي فشل
جديد، و`rule_audit.py` لا يزيد المخالفات (وبعد البند 2 يبقى `rule_audit_ok`).

---

## 6. ما تم التحقق منه فعلياً مقابل ما يتطلب البيئة

- **مُتحقَّق محلياً (بلا playwright):** اختبارات `test_product_matching.py` (24 passed)،
  كسر الحلقة (grep=0)، فشل بوابة التدقيق (EXIT=1, 86 انتهاكاً)، أحجام الملفات (61>150)،
  وجود `input/`، استيرادات playwright (10 ملفات).
- **يتطلب البيئة الكاملة (البند 1):** اختبارات `tawreed_*`, `cli_*`, `streamlit_*`,
  `item_worker_*` (محجوبة حالياً بـ34 خطأ جمع بيئي).
- **مخاطر متبقية بعد التحقق:** لا يمكن إثبات خلو طبقتي tawreed/cli من Regression حتى
  تُثبَّت البيئة وتُجمَع كل الاختبارات (البند 1).
