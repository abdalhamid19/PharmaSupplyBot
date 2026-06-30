# خطة تنظيم ملفات المشروع في مجلدات (File Organization Plan)

> الهدف: تقليل ازدحام الملفات داخل المجلد الواحد، وتقسيمها إلى مجلدات
> فرعية واضحة قائمة على المسؤولية (Domain-Driven)، بحيث يصبح المشروع أسهل
> للفهم والتتبع — **دون أي تغيير في السلوك (Behavior Frozen)**.

---

## 0. ملخص تنفيذي (لماذا هذه الخطة)

المشكلة الحالية: عدد ضخم من ملفات `.py` مكدّسة في مجلد واحد، ما يجعل
فهم المشروع وتتبّعه صعباً جداً. القياس الفعلي للوضع الحالي:

| المجلد | عدد ملفات `.py` المباشرة | الحالة |
| --- | --- | --- |
| `src/core/drug_matching/` | **104** | الأسوأ ازدحاماً — أولوية قصوى |
| `src/tawreed/` | **75** | ازدحام شديد |
| `src/core/` (الجذر المباشر) | **48** | ازدحام شديد |
| `src/ui/` | **31** | ازدحام متوسط |
| `src/cli/` | **20** | ازدحام متوسط |
| `tests/` | **77** | ازدحام شديد (يتبع تقسيم المصدر) |

الحل: تقسيم كل مجلد مزدحم إلى **حِزم فرعية (sub-packages)** مبنية على
الميزة/المسؤولية، مع تحديث الاستيرادات تلقائياً، والحفاظ على نجاح كل
الاختبارات بعد كل خطوة.

> **مبدأ ملزم من `project_guidelines.md` و `starting_prompt.md`:**
> - السلوك مُجمّد: لا ميزات جديدة، لا تغيير منطق. **نقل بنية فقط**.
> - منع تفتيت الملفات (No Micro-files): لا نقسم ملفاً لمجرد رقم؛ بل نجمّع
>   الملفات الموجودة في مجلدات منطقية.
> - تتبّع كل خطوة في git (commit بعد كل مرحلة ناجحة) لإمكانية التراجع.
> - تحديث `PROJECT_MAP.md` ديناميكياً بعد كل مرحلة.
> - تشغيل كل الاختبارات + `tools/rule_audit.py` بعد **كل** تغيير.

---

## 1. خط الأساس الحالي (Baseline — يجب تثبيته قبل البدء)

تم قياس الوضع الحالي فعلياً قبل أي تعديل:

### 1.1 الاختبارات
- الأمر: `python3 tools/run_unit_tests.py`
- النتيجة الحالية: `Ran 368 tests` مع `FAILED (errors=19, skipped=5)`.
- **سبب الأخطاء الـ19: بيئي وليس كوديّاً** — `ModuleNotFoundError: No module
  named 'dotenv'`. الحزمة `python-dotenv>=1.0.0` موجودة في `requirements.txt`
  لكنها **غير مُثبّتة في البيئة الحالية**.
- **إجراء إلزامي قبل البدء:** تثبيت التبعيات حتى يصبح خط الأساس أخضر:
  ```bash
  pip install -r requirements.txt
  ```
  ثم إعادة التشغيل والتأكد أن العدّاد أصبح `0 errors` (عدا التخطّيات
  المقصودة `skipped`). **لا تبدأ إعادة التنظيم قبل أن يكون خط الأساس
  معروفاً وأخضر**، وإلا لن نستطيع تمييز أخطاء النقل عن الأخطاء البيئية.

### 1.2 تدقيق القواعد
- الأمر: `python3 tools/rule_audit.py`
- يُبلّغ حالياً عن مخالفات حجم موجودة مسبقاً (file_lines/function_lines/
  line_length) في ملفات مثل `tawreed_order_summary_build.py`،
  `streamlit_manual_review_input.py` وغيرها.
- **هذه المخالفات ليست من مهمتنا.** مهمتنا تنظيم المجلدات فقط. القاعدة:
  *عدد المخالفات بعد كل مرحلة يجب ألا يزيد عن خط الأساس*. أي مخالفة جديدة
  تظهر بسببنا = خطأ يجب إصلاحه فوراً (غالباً سطر استيراد تجاوز 100 حرف).

### 1.3 آلية الحماية من الانحدار (Regression Gate)
بعد كل مرحلة، يجب أن يتحقق التالي حرفياً:
1. `python3 tools/run_unit_tests.py` ← نفس عدد النجاحات أو أكثر، صفر أخطاء جديدة.
2. `python3 tools/rule_audit.py` ← لا مخالفات جديدة مقارنة بالأساس.
3. `git add -A && git commit` ← حفظ نقطة تراجع.

---

## 2. القيود التقنية الحرجة (يجب مراعاتها في كل نقلة ملف)

هذه نقاط اكتُشفت بالفحص الفعلي للكود، وإهمالها سيكسر المشروع:

### 2.1 الاستيرادات النسبية متشعّبة جداً
- داخل كل حزمة الاستيراد نسبي: `from .x import ...` و`from ..core.x import ...`.
- يوجد **408 موقع استيراد متقاطع** عبر `src`. أي نقل ملف من مجلد إلى مجلد
  فرعي **يغيّر عمقه النسبي** (مثلاً `from .y` تصبح `from ..y`)، ويجب تحديث:
  1. كل الاستيرادات **داخل** الملف المنقول (تتعمّق درجة `.` واحدة).
  2. كل الاستيرادات في الملفات الأخرى التي **تشير إلى** الملف المنقول.

### 2.2 الاستيرادات المؤجّلة داخل الدوال (Lazy imports)
- توجد استيرادات داخل الدوال (مثل
  `from .tawreed_api_flow_cart import ...` داخل دالة في
  `tawreed_api_flow_main.py`). هذه **لا تظهر** في فحص أعلى الملف.
- **إجراء إلزامي:** البحث عن الاستيرادات في كامل الملف (`from .` و`import .`)
  وليس أعلى الملف فقط، عبر `grep` شامل قبل اعتبار النقل مكتملاً.

### 2.3 قائمة استثناءات `tools/rule_audit.py` تحتوي مسارات صريحة
- الملف `tools/rule_audit.py` فيه `EXCEPTED_FILE_LENGTHS` يحوي مسارات نصية
  حرفية مثل:
  - `src/core/drug_matching/indexer.py`
  - `src/core/drug_matching/normalizer.py`
  - `src/tawreed/tawreed.py` ... إلخ.
- **عند نقل أي ملف موجود في هذه القائمة، يجب تحديث مساره داخل
  `rule_audit.py` أيضاً**، وإلا سيُبلّغ التدقيق عن مخالفة كاذبة أو يفقد
  الاستثناء. هذا جزء إلزامي من كل مرحلة تمسّ ملفاً مستثنى.

### 2.4 نقاط الدخول من الجذر والاختبارات تستخدم `src...`
- `run.py` و`streamlit_app.py` والاختبارات (171 سطر `from src.`) تستورد
  عبر المسار المطلق `src.<package>...`.
- أي تغيير في مسار حزمة (مثل `src.core.<module>` → `src.core.<subpkg>.<module>`)
  يجب أن يُحدَّث في:
  - كل ملفات `tests/` (171 موقع `from src.`).
  - `run.py`, `streamlit_app.py`.
  - أي أداة في `tools/` تستورد من `src`.

### 2.5 ملفات `__init__.py`
- كل مجلد فرعي جديد **يجب** أن يحتوي `__init__.py` (مع docstring للوحدة،
  لأن `rule_audit` يتطلب docstring للوحدات العامة).
- إن كان `__init__.py` للحزمة الأم يُصدّر رموزاً (re-exports)، يجب تحديثه
  ليُعيد التصدير من المسار الفرعي الجديد للحفاظ على الواجهة العامة.

### 2.6 منع الاستيراد الدائري (No import cycles)
- التجميع في حزم فرعية قد يكشف دورات استيراد كامنة. عند ظهور `ImportError:
  cannot import ... (circular)`، الحل: نقل الاستيراد إلى داخل الدالة
  (lazy) أو إعادة ترتيب التجميع — **دون** تغيير المنطق.

---

## 3. الهيكل المستهدف (Target Folder Structure)

التجميعات أدناه مبنية على البادئات (prefixes) الفعلية لأسماء الملفات
الموجودة، وعلى مسؤولياتها كما وردت في `project_guidelines.md`. **لا تقسيم
لأي ملف** — فقط نقل ملفات كاملة إلى مجلدات.

### 3.1 `src/core/drug_matching/` (104 ملف ← أولوية P0)

البادئات الواضحة: `ai_*`, `indexer*`, `normalizer*`, `verifier*`,
`trace_log*`, `pipeline*`, `config*`, ومفردات (`pricing.py`, `prompts.py`).

```
src/core/drug_matching/
  __init__.py                 # يبقى + يُحدّث re-exports إن وُجدت
  pipeline.py                 # المنسّق العام (يبقى في الجذر كنقطة دخول)
  ai/                         # كل ملفات ai_* (≈40 ملف)
    __init__.py
    ai_health*.py
    ai_provider_cooldown.py
    ai_review*.py
    ai_rotation*.py
    ai_search*.py
    ai_steps.py
    ai_verify*.py
  indexing/                   # indexer*.py (≈12 ملف)
    __init__.py
    indexer*.py
  normalization/              # normalizer*.py (≈20 ملف)
    __init__.py
    normalizer*.py
  verification/               # verifier*.py (≈11 ملف)
    __init__.py
    verifier*.py
  tracing/                    # trace_log*.py (≈10 ملفات)
    __init__.py
    trace_log*.py
  config/                     # config*.py الخاصة بـ drug_matching (4 ملفات)
    __init__.py
    config*.py
  pipeline/                   # pipeline_*.py الفرعية
    __init__.py
    pipeline_ai.py
    pipeline_io.py
    pipeline_matching.py
  # مفردات تبقى في الجذر: pricing.py, prompts.py
```

> ملاحظة: `pipeline.py` (المنسّق) يبقى في الجذر، بينما `pipeline_*.py`
> المساعدة تنتقل إلى `pipeline/`. هذا يحافظ على نقطة دخول واضحة.

### 3.2 `src/tawreed/` (75 ملف ← أولوية P1)

البادئات الواضحة: `tawreed_api*`, `tawreed_order*`, `tawreed_cart*`,
`tawreed_session*`/`tawreed_auth*`, `tawreed_product*`/`product_export_*`,
`tawreed_match*`, `tawreed_search*`, `tawreed_store*`/`tawreed_summary*`.

```
src/tawreed/
  __init__.py
  tawreed.py                  # TawreedBot الرئيسي يبقى في الجذر
  tawreed_bot_*.py            # نواة البوت تبقى قرب tawreed.py
  selectors.py, tawreed_constants.py, tawreed_dom.py, tawreed_ui.py,
  tawreed_dialogs.py, tawreed_timing.py, tawreed_navigation.py   # عناصر مشتركة منخفضة المستوى
  api/                        # tawreed_api*.py (≈14 ملف)
    __init__.py
  auth/                       # tawreed_auth*, tawreed_session*, *headless_auth* (≈8)
    __init__.py
  cart/                       # tawreed_cart*.py, cart_*  (≈3)
    __init__.py
  order/                      # tawreed_order*.py, order_*.py (≈12)
    __init__.py
  products/                   # tawreed_product*, product_export_*, tawreed_export* (≈12)
    __init__.py
  matching/                   # tawreed_match*, tawreed_search*, tawreed_strategy, aggressive (≈10)
    __init__.py
  store/                      # tawreed_store*, tawreed_summary, tawreed_pricing (≈5)
    __init__.py
  artifacts/                  # tawreed_artifacts*, *_merger.py (≈4)
    __init__.py
```

### 3.3 `src/core/` (48 ملف جذري مباشر ← أولوية P1)

البادئات الواضحة: `manual_review_*` (≈15 ملف — أكبر مجموعة)،
`matching_*`، `product_matching_*`، `order_*`، `database*`،
`cart_removal_*`، وملفات هوية (`*_identity.py`).

```
src/core/
  __init__.py
  config/                     # موجود مسبقاً (لا يتغير)
  drug_matching/              # يُعاد تنظيمه في P0
  utils/                      # موجود مسبقاً (لا يتغير)
  manual_review/              # manual_review_*.py (≈15 ملف)
    __init__.py
  matching/                   # matching_*.py + product_matching_*.py (≈15)
    __init__.py
  ordering/                   # order_*.py (≈7)
    __init__.py
  database/                   # database*.py (≈4)
    __init__.py
  cart_removal/               # cart_removal_*.py, prevented_items.py (≈3)
    __init__.py
  identity/                   # candidate_identity, manufacturer_identity, item_text (≈3)
    __init__.py
  quality/                    # quality_metrics*.py (≈2)
    __init__.py
  # مفردات تبقى في الجذر: artifact_run.py, search_query_templates.py
```

> تنبيه ترابط: `..core.utils` مُشار إليه 33 مرة و`..core.matching_types`
> 15 مرة و`artifact_run` 12 مرة — هذه أعلى نقاط الترابط، لذا تُنقل بحذر
> شديد مع تحديث كل المراجع دفعة واحدة.

### 3.4 `src/ui/` (31 ملف ← أولوية P2)

البادئة الموحّدة `streamlit_*`. التجميع حسب الشاشة/المسؤولية:

```
src/ui/
  __init__.py
  index.css
  streamlit_main.py           # نقطة الدخول تبقى في الجذر
  streamlit_shared.py, streamlit_state*.py   # حالة/مشترك يبقى قرب الجذر
  manual_review/              # streamlit_manual_review*.py (≈6)
    __init__.py
  order/                      # streamlit_order*.py (≈4)
    __init__.py
  auth/                       # streamlit_auth, streamlit_headless_auth (≈2)
    __init__.py
  views/                      # overview, results, process, summary_views, timing*, product_matching, prevented_items
    __init__.py
  fields/                     # streamlit_*_fields.py (ai/excel/profile)
    __init__.py
```

### 3.5 `src/cli/` (20 ملف ← أولوية P2)

```
src/cli/
  __init__.py
  cli_commands.py             # نقطة التجميع تبقى في الجذر
  cli_shared.py
  parsers/                    # cli_parser*.py (≈9)
    __init__.py
  commands/                   # cli_auth, cli_order*, cli_cart_removal*, cli_match_products,
    __init__.py               #   cli_export_products, cli_order_items, item_worker (≈9)
```

### 3.6 `tests/` (77 ملف ← أولوية P3 — اختياري)

الاختبارات تعكس المصدر. يُفضّل عكس بنية `src` الجديدة:
```
tests/
  core/ {drug_matching/, manual_review/, matching/, ...}
  tawreed/ {api/, order/, ...}
  ui/
  cli/
```
> هذا اختياري ويأتي أخيراً، لأن `unittest discover("tests")` يكتشف
> المجلدات الفرعية تلقائياً طالما تحتوي على `__init__.py` أو تتبع نمط
> `test_*.py`. يجب التحقق من أن الاكتشاف ما زال يجد 368 اختباراً.

---

## 4. خطة التنفيذ التسلسلية (Milestones — هدف قابل للتحقق لكل مرحلة)

كل مرحلة = (1) نقل ملفات مجموعة واحدة فقط، (2) تحديث كل الاستيرادات،
(3) تحديث `rule_audit` إن لزم، (4) تشغيل الاختبارات + التدقيق، (5) commit.

> **قاعدة ذهبية:** لا ننتقل لمجموعة جديدة قبل أن تكون الاختبارات خضراء
> 100% للمجموعة الحالية. مجموعة واحدة في كل commit لتسهيل التراجع.

### المرحلة 0 — تثبيت خط الأساس
- معيار النجاح: `pip install -r requirements.txt` ثم
  `python3 tools/run_unit_tests.py` يعطي **0 errors**، وتسجيل عدد
  الاختبارات الناجحة (المتوقع 368) كمرجع.
- commit للحالة النظيفة قبل البدء (إن وُجدت تغييرات بيئية).

### المرحلة P0 — إعادة تنظيم `drug_matching` (الأهم)
تُنفّذ على دفعات فرعية (مجموعة بادئة واحدة لكل commit):
- P0.1: نقل `normalizer*` ← `normalization/`
- P0.2: نقل `indexer*` ← `indexing/`
- P0.3: نقل `verifier*` ← `verification/`
- P0.4: نقل `trace_log*` ← `tracing/`
- P0.5: نقل `ai_*` ← `ai/`
- P0.6: نقل `config*` ← `config/` و`pipeline_*` ← `pipeline/`
- لكل دفعة: تحديث الاستيرادات النسبية + المراجع الخارجية + مسارات
  `rule_audit` المستثناة (indexer.py, normalizer.py, trace_log_*.py,
  verifier_*.py, indexer_*.py, pipeline_*.py مذكورة هناك) + اختبارات.
- معيار النجاح لكل دفعة: الاختبارات خضراء + لا مخالفة تدقيق جديدة.

### المرحلة P1 — إعادة تنظيم `tawreed/` و`core/` الجذري
- P1.1: `tawreed/api/` ← `tawreed_api*`
- P1.2: `tawreed/order/`, `tawreed/cart/`
- P1.3: `tawreed/auth/`, `tawreed/products/`
- P1.4: `tawreed/matching/`, `tawreed/store/`, `tawreed/artifacts/`
- P1.5: `core/manual_review/` ← `manual_review_*` (أكبر مجموعة، الأكثر ترابطاً)
- P1.6: `core/matching/`, `core/ordering/`, `core/database/`,
  `core/cart_removal/`, `core/identity/`, `core/quality/`
- تنبيه: تحديث 171 موقع `from src.` في الاختبارات لكل وحدة تتحرك.

### المرحلة P2 — إعادة تنظيم `ui/` و`cli/`
- P2.1: حزم `ui/` الفرعية.
- P2.2: حزم `cli/` الفرعية (`parsers/`, `commands/`).

### المرحلة P3 — (اختياري) إعادة تنظيم `tests/`
- عكس بنية `src` الجديدة، مع التأكد أن `unittest discover` ما زال يكتشف
  نفس عدد الاختبارات (368).

---

## 5. الإجراء الموحّد لنقل ملف واحد (Checklist تشغيلية)

لكل ملف يُنقل من `A/file.py` إلى `A/sub/file.py`:

1. **حصر المراجع الواردة:**
   `grep -rn "file\b" src tests run.py streamlit_app.py tools` لإيجاد كل
   من يستورد هذا الملف (بالاسم بدون امتداد).
2. **نقل الملف** إلى المجلد الفرعي (مع `git mv` للحفاظ على التاريخ).
3. **إنشاء `__init__.py`** في المجلد الفرعي إن لم يوجد (مع docstring).
4. **تعميق استيرادات الملف المنقول نفسه:** كل `from .x` داخله تصبح
   `from ..x` (لأنه نزل درجة)، وكل `from ..core.y` تصبح `from ...core.y`.
   شمل الاستيرادات المؤجّلة داخل الدوال.
5. **تحديث المراجع الواردة** في كل الملفات الأخرى:
   `from .file` → `from .sub.file`، و`from ..A.file` → `from ..A.sub.file`،
   و`from src.A.file` → `from src.A.sub.file`.
6. **تحديث `tools/rule_audit.py`** إن كان مسار الملف ضمن
   `EXCEPTED_FILE_LENGTHS`.
7. **تحديث `__init__.py` للحزمة الأم** إن كان يُعيد تصدير الرمز.
8. **التحقق:** `python3 tools/run_unit_tests.py` + `python3 tools/rule_audit.py`.
9. **commit** برسالة واضحة، مثل: `refactor(drug_matching): move normalizer* into normalization/`.

> توصية: نقل **مجموعة بادئة كاملة** ثم تحديث الاستيرادات دفعة واحدة أكفأ
> من ملف-ملف، لكن يبقى commit لكل مجموعة للتراجع الآمن.

---

## 6. التحقق النهائي الشامل (بعد كل المراحل)

بعد اكتمال كل المراحل يجب تشغيل وتأكيد كل ما يلي:

1. **الاختبارات الكاملة:**
   `python3 tools/run_unit_tests.py` ← نفس عدد النجاحات (368)، **صفر** أخطاء.
2. **تدقيق القواعد:**
   `python3 tools/rule_audit.py` ← لا مخالفات جديدة مقارنة بخط الأساس.
3. **سلامة الاستيراد لنقاط الدخول:**
   - `python3 -c "import run"` (أو ما يعادله) دون أخطاء استيراد.
   - `python3 -c "import streamlit_app"` دون أخطاء استيراد.
4. **فحص استيراد كامل لكل وحدات `src`:**
   `python3 -c "import importlib,pkgutil,src; [importlib.import_module(m.name)
   for m in pkgutil.walk_packages(src.__path__, 'src.')]"`
   للتأكد من عدم وجود وحدة مكسورة أو دورة استيراد.
5. **تحديث `PROJECT_MAP.md`** بقسم `[ARCHITECTURE]` الجديد ليعكس الهيكل
   المجلدي الجديد، وإفراغ `[ORPHANS & PENDING]` مما يخص هذه المهمة.

---

## 7. سجل المخاطر والمشاكل المكتشفة (Discovered Issues)

> وفق `starting_prompt.md`: لا نُصلح أخطاءً خارج النطاق؛ نسجّلها فقط.

1. **تبعية مفقودة في البيئة:** `python-dotenv` مذكورة في
   `requirements.txt` لكنها غير مُثبّتة، ما يُسبّب 19 خطأ اختبار حالياً.
   *ليست مشكلة كود* — تُحلّ بـ `pip install -r requirements.txt`. يجب
   حلّها قبل البدء لتثبيت خط أساس أخضر.
2. **مخالفات حجم سابقة في `rule_audit`:** عدة ملفات تتجاوز عتبات الطول
   (file_lines/line_length) أصلاً قبل مهمتنا. **خارج نطاق** هذه المهمة
   (تنظيم مجلدات فقط)؛ تُترك كما هي ما لم تتولّد مخالفة جديدة بسبب النقل.
3. **استيرادات مؤجّلة داخل الدوال** في وحدات `tawreed_api_*`: تتطلب فحصاً
   شاملاً للملف (وليس أعلاه فقط) عند النقل لتجنّب كسر خفي.
4. **قائمة مسارات صريحة في `rule_audit.py`:** اقتران هشّ بين أسماء الملفات
   ومسارات الاستثناء؛ كل نقلة ملف مستثنى تتطلب تحديثاً يدوياً متزامناً.

---

## 8. الخلاصة

- **النطاق:** تنظيم مجلدات فقط، بسلوك مجمّد، على مراحل صغيرة قابلة للتراجع.
- **الأولوية:** `drug_matching` (104) ثم `tawreed` (75) ثم `core` (48) ثم
  `ui`/`cli`، وأخيراً `tests` (اختياري).
- **بوابة الجودة بعد كل خطوة:** اختبارات خضراء + لا مخالفة تدقيق جديدة +
  commit.
- **شرط الإنجاز:** تشغيل **كل** الاختبارات والتأكد أن كل شيء يعمل بعد كل
  تغيير، وهو منصوص عليه صراحةً في هذه الخطة (المرحلة 0، القسم 4، القسم 6).
