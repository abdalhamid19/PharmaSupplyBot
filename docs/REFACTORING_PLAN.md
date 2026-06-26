# خطة إعادة الهيكلة الشاملة (Comprehensive Refactoring Plan)

> هذه الخطة مبنية على قياس فعلي للمستودع وليست على تقديرات. كل رقم مذكور أدناه
> مأخوذ من تشغيل `tools/rule_audit.py` و `tools/run_unit_tests.py` و `wc -l`.
> الهدف: إعادة هيكلة جراحية تحافظ على السلوك، تعيد بوابة الجودة إلى اللون الأخضر،
> وتقلّص الدين التقني المتراكم حول حدود منطقية واضحة.

---

## 1. المبادئ الحاكمة (Governing Principles)

تلتزم هذه الخطة حرفياً بـ `docs/project_guidelines.md` وببروتوكولات
`docs/starting_prompt.md`:

- **عدم تغيير السلوك (No Behavior Change):** إعادة الهيكلة لا تغيّر أي منطق عمل.
  أي تغيير سلوكي خارج نطاق هذه الخطة ويحتاج مهمة منفصلة.
- **Simplicity First / No Feature Creep:** لا نضيف طبقات تجريد أو ميزات لم تُطلب.
  لا نجرّد كوداً يُستخدم مرة واحدة فقط.
- **التقسيم حول حدود منطقية (Logical Seams) لا تقطيع آلي:** عند تجاوز ملف للحد،
  نفصله حول مسؤولية واضحة، لا لمجرد إرضاء رقم. (متوافق مع قاعدة Refactoring في
  `project_guidelines.md`).
- **الحفاظ على الواجهات العامة (Preserve Public Interfaces):** أي نقل لوحدة يجب أن
  يبقي الاستيرادات العامة تعمل، أو يُخطَّط ويُختبر صراحةً.
- **فصل المسؤوليات:** منطق العمل (parsing/matching/scoring/validation) منفصل عن
  Playwright و CLI و Streamlit. الجانب الجانبي (side effects) يبقى في طبقات
  التكامل (`tawreed*.py`, `streamlit_*.py`, CLI wiring).
- **التحقق بعد كل تغيير (Loop Until Verified):** بعد كل خطوة تشغيل
  `tools/run_unit_tests.py` + `tools/rule_audit.py`. لا انتقال للخطوة التالية قبل
  تحقق معيار النجاح. لا Regression.

---

## 2. الحالة الحالية المقاسة (Measured Baseline)

> مرجع التشغيل: استخدم مفسّر البيئة الافتراضية `.venv/bin/python` لأن مفسّر النظام
> ينقصه `python-dotenv` و `playwright` (معرّفان في `requirements.txt`).

### 2.1 الاختبارات
- `.venv/bin/python tools/run_unit_tests.py` → **429 اختبار، النتيجة OK (تنجح كلها).**
- مفسّر النظام (`python3`) يفشل في استيراد 34 وحدة اختبار بسبب نقص `dotenv` و
  `playwright` فقط — هذه مشكلة بيئة وليست فشل اختبار.

### 2.2 بوابة الجودة (rule_audit)
- `tools/rule_audit.py` **يفشل حالياً (exit=1)** بـ **116 مخالفة غير متوقعة** خارج
  خط الأساس المقبول:
  - `function_lines`: 49 (دوال > 20 سطراً)
  - `line_length`: 44 (أسطر > 100 محرف)
  - `file_lines`: 23 (ملفات > 100 سطر تجاوزت خط الأساس)
- آلية البوابة (مصدر الحقيقة): `MAX_FILE_LINES=100`, `MAX_FUNCTION_LINES=20`,
  `MAX_LINE_LENGTH=100`، مع `EXCEPTED_FILE_LENGTHS` (9 ملفات مستثناة) و
  `BASELINE_VIOLATIONS` (دين تقني مقبول). البوابة تفشل فقط على مخالفات **جديدة**.

### 2.3 الانحراف الجوهري (Drift)
البوابة كانت خضراء سابقاً، لكن ملفات نمت بعد التقاط خط الأساس فأصبحت تتجاوز الحد.
**23 ملفاً جديداً تجاوز 100 سطر** (أبرزها):

| الملف | الأسطر |
|---|---|
| `src/ui/streamlit_manual_review.py` | 219 |
| `src/core/manual_review_runtime.py` | 214 |
| `src/tawreed/tawreed_api.py` | 198 |
| `src/tawreed/tawreed_api_flow.py` | 193 |
| `src/core/quality_metrics.py` | 175 |
| `src/core/order_run_artifact_rows.py` | 170 |
| `src/tawreed/tawreed_api_matching.py` | 163 |
| `src/tawreed/tawreed_order_run_artifacts.py` | 160 |
| `src/core/database.py` | 157 |
| `src/ui/streamlit_manual_review_page_saved.py` | 151 |
| `src/tawreed/tawreed_api_discovery_enhanced.py` | 147 |
| `src/tawreed/tawreed_search_logic.py` | 134 |
| (+ 11 ملفاً آخر بين 101 و 117 سطراً) | |

### 2.4 الملفات الأكبر (دين معماري قائم، أغلبه ضمن الاستثناءات/خط الأساس)
القيم الفعلية من `wc -l` (الخطة القديمة أغفلت أكبر 5 ملفات):

| الملف | الأسطر | ملاحظة |
|---|---|---|
| `src/core/drug_matching/normalizer.py` | 1327 | الأكبر — مستثنى حالياً |
| `src/core/product_matching.py` | 1117 | مستثنى |
| `src/core/drug_matching/trace_log.py` | 1061 | باقٍ في خط الأساس |
| `src/core/drug_matching/ai_steps.py` | 1037 | باقٍ في خط الأساس |
| `src/core/drug_matching/verifier.py` | 987 | باقٍ في خط الأساس |
| `src/tawreed/tawreed.py` | 976 | مستثنى |
| `src/core/drug_matching/indexer.py` | 561 | مستثنى |
| `src/cli/cli_order.py` | 478 | باقٍ في خط الأساس |
| `src/core/drug_matching/pipeline.py` | 464 | باقٍ في خط الأساس |

### 2.5 المخاطر الأمنية المؤكدة
- `src/core/database.py:21-25`: قيم اتصال سحابية مشفّرة داخل الكود:
  - `DEFAULT_HOST = "mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud"`
  - `DEFAULT_USER = "abdalhamid"`, `DEFAULT_DATABASE = "defaultdb"`
  - كلمة المرور **ليست** مشفّرة (تُقرأ من البيئة فقط) — وهذا جيد، لكن تسريب
    المضيف واسم المستخدم وقاعدة البيانات يبقى مشكلة أمنية حقيقية.

### 2.6 ما هو **منجَز بالفعل** (تصحيح للخطة القديمة)
- نظام الإعدادات مُنظَّم مسبقاً في `src/core/config/` (`config.py`,
  `config_factory.py`, `config_models.py`, `config_updater.py`) — اقتراح
  "إعادة تنظيم config" في الخطة القديمة شبه منجَز.
- مطابقة الأدوية مقسّمة مسبقاً داخل `src/core/drug_matching/` إلى وحدات متعددة
  (`normalizer`, `indexer`, `pipeline`, `verifier`, `ai_steps`, `ai_rotation`,
  `trace_log`, `prompts`, ...).
- `src/core/utils/` موجود (`excel.py`, `chunking.py`, `playwright_browser.py`).

> الخلاصة: المشكلة لم تعد "لا يوجد تقسيم"، بل **انحراف البوابة** + **ملفات منطق
> ضخمة لم تُفصل حول حدود نظيفة** + **ثغرة بيانات اتصال مشفّرة**.

---

## 3. معايير النجاح القابلة للتحقق (Verifiable Goals)

| # | المعيار | كيفية التحقق |
|---|---|---|
| G1 | `tools/rule_audit.py` يطبع `rule_audit_ok` ويعيد exit=0 | تشغيل الأمر |
| G2 | `429/429` اختبار يبقى ناجحاً (لا Regression) بعد كل مرحلة | `tools/run_unit_tests.py` |
| G3 | إزالة بيانات الاتصال المشفّرة من `database.py` مع بقاء الاختبارات خضراء | مراجعة + اختبار |
| G4 | كل ملف منطق مُعاد هيكلته ≤ 100 سطر أو مُبرَّر صراحةً في الاستثناءات | المقارنة مع `wc -l` |
| G5 | لا تغيّر في أي سلوك عام (نفس المخرجات لنفس المدخلات) | اختبارات مرتبطة + تشغيل دخان |
| G6 | تقليص عدد عناصر `BASELINE_VIOLATIONS` تدريجياً (دين أقل) | فرق العدّ قبل/بعد |

> ملاحظة مهمة حول الهدف الرقمي: المعيار ليس "أقل من 500 سطر" (كما في الخطة
> القديمة، وهو يناقض بوابة المشروع)، بل **بوابة المشروع نفسها: 100 سطر/ملف و
> 20 سطر/دالة و100 محرف/سطر**، مع استثناءات مُبرَّرة عند الحاجة.

---

## 4. الأولويات معاد ترتيبها بالأدلة

### 🔴 P0 — أمان + استعادة بوابة الجودة

#### P0.1 إزالة بيانات الاتصال المشفّرة (`src/core/database.py`)
- **المشكلة:** أسطر 21-25 تحوي مضيفاً واسم مستخدم وقاعدة بيانات حقيقية.
- **الحل (جراحي، يحافظ على السلوك):**
  - نقل القيم الافتراضية إلى الإعداد الخارجي (`.env` / `config.yaml`) بدل ثوابت
    المصدر؛ الاعتماد على `os.getenv("DB_HOST")` ... إلخ.
  - عند غياب أي قيمة مطلوبة، رفع `RuntimeError` واضح (كما هو معمول به الآن مع
    `DB_PASSWORD`) بدل اللجوء لقيمة سحابية مشفّرة.
  - تحديث `.env.example` بالمفاتيح المطلوبة دون قيم حقيقية.
- **معيار النجاح:** لا قيم سرّية في المصدر؛ الاختبارات خضراء؛ التشغيل يعمل عند
  ضبط متغيرات البيئة. (G3)
- **خطر:** أي كود يفترض الاتصال الافتراضي بدون بيئة سيفشل بوضوح — مقصود.

#### P0.2 إعادة البوابة إلى الأخضر (116 مخالفة غير متوقعة)
هذا هو محور "إعادة الهيكلة الشاملة" الحقيقي. لكل مخالفة، أحد مسارين فقط:
- **(أ) إصلاح حقيقي** عبر تقسيم/تقصير حول حدّ منطقي (مفضّل لملفات المنطق).
- **(ب) قبول مُبرَّر** بإضافة المخالفة إلى `BASELINE_VIOLATIONS` أو
  `EXCEPTED_FILE_LENGTHS` **فقط** عندما يكون التقسيم سيضر بالوضوح/التماسك.
- التوزيع: 49 `function_lines` + 44 `line_length` + 23 `file_lines`.
  - `line_length` (44): الأسهل والأقل خطراً — كسر الأسطر دون تغيير منطق.
  - `function_lines` (49): استخراج دوال مساعدة خاصة (`_helper`) حول خطوات واضحة.
  - `file_lines` (23): فصل وحدات (انظر P1/P2).
- **معيار النجاح:** `rule_audit_ok` + exit=0 (G1) مع بقاء الاختبارات خضراء (G2).

---

### 🟠 P1 — ملفات المنطق الضخمة (فصل حول حدود نظيفة)

> ترتيب حسب الحجم والأثر. كل عملية: فصل وحدة جديدة + إبقاء الواجهة العامة + اختبار.

#### P1.1 `src/core/drug_matching/normalizer.py` (1327 سطر)
- أكبر ملف في المشروع ولم تذكره الخطة القديمة.
- حدود الفصل المقترحة (مسؤوليات قائمة فعلاً داخل الملف): تطبيع النص الخام،
  تحليل الدواء (`parse_drug`)، اشتقاق الجرعة المفقودة، مطابقة المكوّنات
  (`components_match`)، اشتقاقات العلامة التجارية.
- اقتراح: `normalizer.py` (واجهة) + `normalizer_parsing.py` +
  `normalizer_components.py` + `normalizer_brand.py`.

#### P1.2 `src/core/product_matching.py` (1117 سطر)
- فصل: بناء الفهرس/الاستعلام، حساب الدرجات، قواعد القبول/الرفض، تجميع النتائج.
- إبقاء نقاط الدخول العامة كما هي (مستوردة في CLI/UI/tawreed).

#### P1.3 `src/core/drug_matching/trace_log.py` (1061 سطر)
- ملف تسجيل/تتبّع: فصل كتّاب الأحداث حسب المرحلة
  (candidate / score / fuzzy / ai_verify / ai_search / ai_review / summary).
- أغلب دواله مسجّلة في خط الأساس → فرصة لتقليص `BASELINE_VIOLATIONS` (G6).

#### P1.4 `src/core/drug_matching/ai_steps.py` (1037 سطر)
- يتوافق مع اقتراح "مراحل المطابقة بالذكاء الاصطناعي": verification / search /
  review كوحدات منفصلة خلف منسّق رفيع.
- **حذر:** منطق حسّاس لاستدعاءات AI؛ التقسيم سلوكي-حيادي فقط، مع اختبارات
  `test_order_ai_matching.py` و `test_ai_*` كشبكة أمان.

#### P1.5 `src/core/drug_matching/verifier.py` (987 سطر)
- `_call_api` وحدها 202 سطر. فصل: بناء الطلب، استخراج JSON، تطبيق نتيجة التحقق،
  مسار المراجعة، إيجاد بديل أفضل.

#### P1.6 `src/tawreed/tawreed.py` (976 سطر)
- منسّق `TawreedBot` يخلط Auth/Order/Cart. فصل التدفقات إلى وحدات خلف منسّق
  رفيع مع الحفاظ على واجهة `TawreedBot` العامة:
  `tawreed_auth_flow` / `tawreed_order_flow` / `tawreed_cart_flow` (يُعاد
  استخدام `tawreed_cart_removal.py` القائم).
- **حذر:** أكثر ملف ملامسةً لـ Playwright؛ غطِّ بـ `test_tawreed_bot.py`.

#### P1.7 `src/cli/cli_order.py` (478 سطر)
- استخراج منطق التوازي (`_run_parallel_order`) ومنطق تحميل/تصفية العناصر إلى
  وحدات (يُعاد استخدام `item_worker_*` القائمة). إبقاء أمر CLI رفيعاً.

#### P1.8 `src/core/drug_matching/indexer.py` (561 سطر)
- `best_match_detailed` 96 سطراً. فصل بناء الفهرس عن منطق البحث عن أفضل تطابق.

---

### 🟡 P2 — تجمّعات مخالفات في طبقة UI و artifacts

> ملفات تجاوزت 100 سطر حديثاً وتركّز فيها line_length/function_lines.

- `src/ui/streamlit_manual_review.py` (219 سطر، 10 مخالفات): دالة
  `render_manual_review_editor` 138 سطراً + أسطر طويلة كثيرة. فصل المُحرِّر إلى
  مكوّنات عرض أصغر (الصفحة، النموذج، القرارات المحفوظة) — جزئياً موجود في
  `streamlit_manual_review_page_*`.
- `src/ui/streamlit_manual_review_page_saved.py` (151، 9 مخالفات): أسطر طويلة +
  `render_saved_decisions` 101 سطراً.
- `src/ui/streamlit_overview.py` (112، 7 مخالفات): أسطر طويلة في قسم الإعدادات.
- `src/core/manual_review_runtime.py` (214، 7 مخالفات).
- `src/core/quality_metrics.py` و `src/core/order_run_artifact_rows.py` و
  `src/tawreed/tawreed_order_run_artifacts.py` (5 مخالفات لكل منها).
- `src/tawreed/tawreed_api_flow.py` / `tawreed_api_matching.py` /
  `tawreed_api_discovery_enhanced.py`: فصل بناء الحمولات عن تنفيذ الطلب.

---

### 🟢 P3 — تنظيم بنيوي خفيف (أغلبه شبه منجَز)

- **CLI Parsers:** يوجد 11+ ملف `cli_parser_*.py`. التكرار الحقيقي في الخيارات
  المشتركة → استخراج `cli_parser_shared.py` (موجود) كقاعدة موحّدة بدل دمج
  الملفات (الدمج يخالف مبدأ الوحدات الصغيرة المركّزة).
- **Config:** `src/core/config/` منظّم مسبقاً؛ يكفي إصلاح مخالفات
  `config_factory.py` (دالة `build_matching_config` 27 سطراً) و`config_updater.py`.
- **Utils:** `src/core/utils/` منظّم؛ لا حاجة لإعادة هيكلة، فقط ضبط الأسطر.

---

## 5. منهجية التنفيذ لكل ملف (Surgical Method)

لكل ملف في P0.2/P1/P2:
1. **تحليل الأثر:** تتبّع مستوردي الوحدة (CLI/UI/tawreed/tests) قبل أي نقل.
2. **تحديد الحدّ المنطقي:** مسؤولية واحدة واضحة قابلة للفصل (لا تقطيع آلي).
3. **الاستخراج:** إنشاء الوحدة الجديدة + إعادة التصدير من الوحدة الأصلية للحفاظ
   على الواجهة العامة.
4. **التحقق الفوري:** `tools/run_unit_tests.py` (429 أخضر) + `tools/rule_audit.py`.
5. **مزامنة الخريطة:** تحديث `PROJECT_MAP.md` (قسم `[ARCHITECTURE]`) وإفراغ ما
   اكتمل من `[ORPHANS & PENDING]`.
6. **تحديث الدين:** عند إصلاح مخالفة بخط الأساس، حذفها من `BASELINE_VIOLATIONS`؛
   عند قبول مخالفة جديدة مُبرَّرة، إضافتها بدلاً من ترك البوابة حمراء.

---

## 6. خطة المراحل (Milestones)

> كل مرحلة لها معيار خروج قابل للتحقق؛ لا انتقال قبل تحققه.

### المرحلة 0 — تثبيت البيئة والبوابة (نصف يوم)
- تثبيت تبعيات `requirements.txt` المفقودة في بيئة التشغيل، أو اعتماد `.venv`.
- توثيق أمر التحقق الموحّد: `.venv/bin/python tools/run_unit_tests.py` +
  `.venv/bin/python tools/rule_audit.py`.
- **خروج:** 429 اختبار أخضر + لقطة أساس واضحة لعدد المخالفات (116).

### المرحلة 1 — الأمان (يوم)
- تنفيذ P0.1 (database.py).
- **خروج:** لا أسرار في المصدر + 429 أخضر. (G3)

### المرحلة 2 — استعادة البوابة الخضراء (2–3 أيام)
- تنفيذ P0.2: معالجة 116 مخالفة (line_length أولاً، ثم function_lines، ثم
  file_lines الصغيرة في P2).
- **خروج:** `rule_audit_ok` + exit=0 + 429 أخضر. (G1, G2)

### المرحلة 3 — ملفات المنطق الضخمة (4–6 أيام)
- تنفيذ P1.1 → P1.8 بالترتيب، ملف واحد في كل دفعة مع تحقق كامل بينها.
- **خروج:** كل ملف مفصول ≤ 100 سطر أو استثناء مُبرَّر + 429 أخضر + تقلّص خط
  الأساس. (G4, G6)

### المرحلة 4 — تنظيف P3 والإغلاق (1–2 يوم)
- توحيد خيارات الـ parser المشتركة، ضبط config/utils، تحديث `PROJECT_MAP.md`.
- **خروج:** البوابة خضراء، الاختبارات خضراء، الخريطة محدّثة، `[ORPHANS]` فارغ.

---

## 7. بروتوكول التحقق (Verification Protocol)

بعد **كل** تغيير، وبدون استثناء:

```bash
.venv/bin/python tools/run_unit_tests.py   # يجب: Ran 429 ... OK
.venv/bin/python tools/rule_audit.py       # هدف نهائي: rule_audit_ok (exit 0)
```

- عند تغيير منطق المطابقة/التحليل/الجلسة: إضافة أو تحديث اختبار مركّز مرتبط
  بالملف المتغيّر قبل الإغلاق.
- لتغييرات UI/Streamlit: تشغيل دخان سريع للواجهة عند الحاجة بالإضافة للاختبارات.
- لا يُعلن اكتمال مرحلة إلا بعد خضرة الاختبارات والبوابة معاً.

---

## 8. مخاطر وملاحظات

1. **حساسية ملفات AI و Playwright:** `ai_steps.py`, `verifier.py`, `tawreed.py`
   تحوي تكاملات خارجية؛ التقسيم يجب أن يكون سلوكي-حيادي 100% ومغطّى باختبارات
   موجودة (`test_ai_*`, `test_tawreed_*`).
2. **خط الأساس مصدر حقيقة حي:** أي مخالفة جديدة مقبولة تُضاف إلى
   `BASELINE_VIOLATIONS`؛ وأي مخالفة مُصلَحة تُحذف منه ليبقى الملف دقيقاً.
3. **تجنّب التفتيت المفرط (No Micro-files):** لا نُنشئ ملفات بدالة واحدة تافهة؛
   الفصل حول مسؤولية حقيقية فقط.
4. **بيئة التشغيل:** يجب استخدام `.venv` (به كل التبعيات) أو تثبيت
   `python-dotenv` و`playwright` في بيئة النظام قبل تشغيل الاختبارات.
5. **مزامنة الخريطة (State Sync):** `PROJECT_MAP.md` يُحدَّث مع كل نقل وحدة؛ هو
   الذاكرة الخارجية المعتمدة وفق `starting_prompt.md`.

---

## 9. مصدر الحقيقة (Source of Truth)

- بوابة الجودة: `tools/rule_audit.py` (100 سطر/ملف، 20 سطر/دالة، 100 محرف/سطر،
  مع الاستثناءات وخط الأساس).
- القواعد: `docs/project_guidelines.md`.
- البروتوكولات: `docs/starting_prompt.md`.
- الذاكرة الخارجية: `PROJECT_MAP.md`.
- التحقق: `tools/run_unit_tests.py` (429 اختباراً).
