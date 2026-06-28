# خطة إعادة الهيكلة المعمارية — PharmaSupplyBot

> **النوع:** خطة (Plan only) — لا يوجد تنفيذ كود في هذا المستند.
> **القاعدة الحاكمة:** السلوك مُجمَّد (Behavior Frozen). كل تغيير هيكلي فقط، ممنوع
> إضافة ميزات أو تغيير منطق العمل.
> **مرجع القواعد:** `docs/project_guidelines.md` + `docs/starting_prompt.md`.
> **تاريخ التشخيص:** 2026-06-28
> **أداة التحقق الرسمية:** `python3 tools/rule_audit.py` و `python3 -m pytest`.

---

## 0. ملخص تنفيذي (Executive Summary)

المشروع **يعمل وظيفياً** ومُقسَّم بالفعل إلى طبقات اسمية
(`cli`, `core`, `tawreed`, `ui`). لكن التشخيص الميداني كشف أن المشكلة الجوهرية
ليست "مونوليث متضخم"، بل **العكس تماماً: تفتيت مُفرط (Over-Fragmentation /
Shotgun Architecture)** يتعارض مباشرة مع تعليمة `starting_prompt.md`:
«التقسيم المعتمد على الميزات مع منع تفتيت الملفات (No Micro-files)».

### الأرقام المُقاسة (أدلة ملموسة)

| المؤشر | القيمة المقاسة | المصدر |
|---|---|---|
| ملفات Python داخل `src/` | **434** | `find src -name '*.py'` |
| إجمالي أسطر `src/` | **29,457** | `wc -l` |
| ملفات تحت 30 سطر | **70** | تحليل `wc -l` |
| ملفات تحت 50 سطر | **151** | تحليل `wc -l` |
| متوسط حجم الملف | **~68 سطر/ملف** | 29457 / 434 |
| مخالفات تدقيق جديدة (خارج baseline) | **336** | `rule_audit.py` |
| مخالفات baseline مقبولة سلفاً | **~190** | `BASELINE_VIOLATIONS` |
| أخطاء جمع الاختبارات | **28–31** | `pytest --co` |
| اختبارات تُجمع بنجاح | **281** | `pytest --co` |
| ملفات توثيق `docs/*.md` | **52** | `ls docs/*.md` |

### الخلاصة المعمارية بإيجاز

1. **تفتيت مُفرط**: وحدات منطقية واحدة مُمزَّقة عبر 11–20 ملفاً صغيراً
   (مثل `ai_rotation_config_*` = 11 ملفاً بمتوسط 27 سطراً).
2. **حلقة استيراد (Import Cycle) حرجة** بين `core` و `tawreed`.
3. **تسريب طبقي**: استيراد `playwright` على مستوى الـ module يُسقط اختبارات
   الوحدة النقية (28 خطأ جمع عند غياب playwright).
4. **فوضى الجذر**: ملفات سكربتات ومخرجات JSON سائبة في جذر المشروع.
5. **ازدواجية مجلدات الإدخال**: `input/` و `data/input/` متوازيان.

---

## 1. التشخيص التفصيلي (Evidence-Based Diagnosis)

### 1.1 خريطة الطبقات الفعلية الحالية

```
run.py            → نقطة دخول CLI (transport)         [نظيف، 41 سطر]
streamlit_app.py  → نقطة دخول GUI (transport)         [نظيف، 10 أسطر]
src/cli/          → 38 ملف  — تحليل وسائط + أوامر CLI  (transport + controller)
src/ui/           → 54 ملف  — Streamlit (transport/presentation)
src/tawreed/      → 114 ملف — Playwright + API (integration layer)
src/core/         → 227 ملف — منطق العمل + بيانات     (business + data)
  ├─ config/      → إعدادات (4 ملفات)
  ├─ drug_matching/ → ~120 ملف (أسوأ بؤرة تفتيت)
  └─ utils/       → excel + playwright_browser (7 ملفات)
```

### 1.2 مطابقة الطبقات على نموذج `project_guidelines.md`

| الطبقة المطلوبة | الموقع الحالي | الحالة |
|---|---|---|
| Transport (Network/Protocols) | `run.py`, `streamlit_app.py`, `cli/cli_parser*`, `ui/streamlit_*` | موجود |
| Controllers/Handlers | `cli/cli_commands.py`, `cli/cli_*_main.py` | موجود لكن مُفتَّت |
| Services (Business Logic) | `core/product_matching*`, `core/matching_*`, `core/drug_matching/`, `core/order_ai_*` | موجود لكن مُفتَّت بشدة |
| Repositories / Data Access | `core/database*.py`, `core/manual_review_store*.py` | موجود ونظيف نسبياً |
| Data Modeling / Types | `core/matching_models.py`, dataclasses متناثرة | مُشتَّت |
| Config & Constants | `core/config/`, ملفات `*_constants.py` كثيرة | مُشتَّت |
| Integration (لا يخص نموذج HTTP بل المتصفح) | `src/tawreed/` | موجود |

### 1.3 طبقة الوصول للبيانات (Data Access) — أنظف جزء

- **المحرك:** CockroachDB Cloud عبر `psycopg2` (لا SQLite في الكود).
  - دليل: `database_pool.py:7,31`, `database_credentials.py:29` (port 26257),
    `database.py:3`.
- **التجريد موجود ونظيف عموماً** عبر سلسلة:
  `DatabaseCredentials → DatabasePool → DatabaseQueries → DatabaseManager →
  ManualReviewStore (repository) → SQL constants (store_sql.py)`.
- **مخالفات بسيطة (لا تكسر الطبقة لكنها غير متسقة):**
  - `manual_review_store.py:81-85`: `upsert_batch` يفتح cursor يدوياً بدل
    المرور عبر `execute_update()`.
  - `manual_review_store.py:116`: نص SQL خام مضمَّن بدل وضعه في `store_sql.py`.
  - `manual_review_store_helpers.py:47`: نص SQL خام مضمَّن.
- **UI لا يلمس قاعدة البيانات مباشرة** — يمر دائماً عبر `ManualReviewStore`.
  ملاحظة: `streamlit_manual_review_data.py:16,65` يُنشئ `ManualReviewStore`
  مباشرة بدل المرور عبر حارس الأخطاء `manual_review_store_or_stop()`.

### 1.4 حلقة الاستيراد الحرجة (Import Cycle) — الخطر الأعلى

- `core → tawreed`: `src/core/cart_removal_summary.py:7`
  `from ..tawreed.tawreed_artifacts import append_csv_artifact`
- `tawreed → core`: `src/tawreed/tawreed_cart_removal_core.py:8`
  `from ..core.cart_removal_summary import CartRemovalSummary, append_cart_removal_summary`
- **النتيجة:** حلقة استيراد متبادلة مباشرة. والأسوأ: `tawreed_artifacts.py:6`
  يستورد `from playwright.sync_api import Page`، أي أن تحميل وحدة منطق العمل
  `cart_removal_summary` يجرّ Playwright إلى طبقة الأعمال عند الاستيراد.
- هذا انعكاس لاتجاه التبعية الذي يفرضه `project_guidelines.md`:
  «التبعيات تتحرك للداخل نحو المنطق القابل لإعادة الاستخدام».

### 1.5 تسريب Playwright على مستوى الـ module — يكسر اختبارات الوحدة

- `playwright` مُدرج في `requirements.txt` لكنه **غير مثبت في بيئة التشغيل
  الحالية**، فينتج **28 خطأ جمع** في pytest.
- السبب: `src/tawreed/tawreed_api_main.py:8`
  `from playwright.sync_api import sync_playwright` على مستوى الوحدة، يُنفَّذ
  عند مجرد استيراد أي شيء من `tawreed`.
- الاختبارات النقية (core) تمر: **45 passed** عند تشغيلها منفصلة.
- ملاحظة معمارية: `src/core/utils/playwright_browser.py` أداة واعية بـPlaywright
  تعيش داخل `core/utils` — موضعها الأنسب طبقة integration.

### 1.6 أسوأ بؤر التفتيت (Top Fragmentation Offenders)

| الترتيب | المجموعة (Cluster) | الطبقة | عدد الملفات | إجمالي الأسطر | متوسط |
|---|---|---|---|---|---|
| 1 | `ai_rotation_config_*` | drug_matching | 11 | 294 | **27** |
| 2 | `ai_rotation_*` (كامل) | drug_matching | 20 | 844 | 42 |
| 3 | `cli_parser_*` | cli | 12 | 494 | **41** |
| 4 | `pipeline_*` | drug_matching | 11 | 535 | 49 |
| 5 | `trace_log_*` | drug_matching | 19 | 1,631 | 86 |
| 6 | `verifier_*` | drug_matching | 19 | 1,586 | 83 |
| 7 | `product_matching_*` | core | 18 | 1,334 | 74 |
| 8 | `tawreed_api_*` | tawreed | 18 | 1,203 | 67 |
| 9 | `streamlit_manual_review_*` | ui | 16 | 1,274 | 80 |
| 10 | `manual_review_*` | core | 13 | 1,050 | 81 |
| 11 | `tawreed_order_*` | tawreed | 13 | 1,071 | 82 |
| 12 | `indexer_*` | drug_matching | 12 | 1,163 | 97 |

أمثلة على الفتات الصريح (Stubs):
- `ai_rotation_config_cerebras.py` = 13 سطر، `..._opencode.py` = 15،
  `..._groq.py` = 17 (ملف لكل مزوّد AI).
- `cli_parser_manual_review_search.py` = 14 سطر.
- `tawreed_products_flow_dialog.py` = 14 سطر.
- `order_run_artifact_rows.py` = 19، `..._constants.py` = 20.

### 1.7 فوضى الجذر والتوثيق

- **سكربتات سائبة في الجذر** يجب أن تكون داخل `tools/`:
  `add_avil_to_cockroachdb.py`, `create_test_avil.py`, `diagnose_avil.py`.
- **مخرجات/تشخيص سائبة** يجب حذفها أو نقلها إلى `artifacts/`:
  `output.json`, `output3.json`, `output_decision.json`,
  `login_test_result.txt`, `product_matching_functions.txt`,
  `test_avil_fix.xlsx`.
- **ازدواجية الإدخال:** `input/` و `data/input/` متوازيان — يجب توحيد المصدر.
- **تضخم التوثيق:** 52 ملف `.md` في `docs/` (تقارير سابقة متراكمة) —
  يُؤرشَف معظمها لتقليل التشويش (لا يؤثر على الكود).

---

## 2. المبادئ الحاكمة للتنفيذ (Guardrails)

1. **السلوك مُجمَّد:** لا تغيير في منطق المطابقة، الطلب، أو الإزالة.
   إعادة الهيكلة = نقل/دمج/إعادة تسمية فقط.
2. **التوحيد لا التفتيت:** الهدف العكسي للوضع الحالي — دمج الفتات في وحدات
   متماسكة موجَّهة بالميزة (Feature-Oriented)، مع احترام عتبة 100 سطر للملف
   و20 سطر للدالة *عندما لا يضر ذلك بالوضوح* (القاعدة صريحة بهذا الاستثناء).
3. **خطوة = commit:** كل دمج أو نقل في commit مستقل قابل للارتداد عبر git.
4. **بوابة التحقق بعد كل خطوة:**
   `python3 tools/rule_audit.py` يجب أن يُخرج `rule_audit_ok` (أو يقل العدد)،
   و`python3 -m pytest` للاختبارات المرتبطة بالجزء المُعدَّل.
5. **حافظ على الواجهات العامة:** أي دمج لملفات يجب أن يُبقي مسارات الاستيراد
   العامة تعمل (عبر re-export في `__init__.py` أو ملف الواجهة) لتجنب Regression.
6. **اكتشفتَ خللاً؟ لا تصلحه — سجِّله** في قسم «ملاحظات/مشكلات مكتشفة».

---

## 3. الخطة مرتبة حسب الأولوية والخطورة

ترتيب التنفيذ مصمَّم بحيث **تُزال المخاطر البنيوية أولاً** (التي تمنع
التطوير الآمن)، ثم التوحيد، ثم التجميل.

---

### المرحلة P0 — تثبيت البيئة وكسر المخاطر البنيوية (حرجة)

> الهدف: جعل قاعدة الكود **قابلة للاختبار والتطوير بأمان** قبل أي نقل واسع.
> لا يجوز البدء بالتوحيد الكبير قبل اكتمال هذه المرحلة.

#### P0.1 — توثيق خط الأساس قبل أي تغيير
- **المطلوب:** تثبيت `playwright` في بيئة التطوير ثم تشغيل:
  - `pip install -r requirements.txt && playwright install chromium`
  - `python3 -m pytest -q` ← التقاط عدد الاختبارات الناجحة كـ baseline.
  - `python3 tools/rule_audit.py` ← التقاط عدد المخالفات الحالي كـ baseline.
- **الخطورة:** بدون baseline لا يمكن إثبات «لا Regression».
- **معيار النجاح:** قائمة اختبارات ناجحة معروفة + عدد مخالفات معروف، محفوظان.

#### P0.2 — كسر حلقة الاستيراد `core ↔ tawreed` (الخطر الأعلى)
- **المشكلة:** `core/cart_removal_summary.py:7` ↔ `tawreed_cart_removal_core.py:8`.
- **الحل المعماري:** الفصل بين *النموذج* (Data Model) و*الكتابة* (I/O/Artifact):
  - يبقى `CartRemovalSummary` (dataclass نقي) داخل `core` بلا أي استيراد من
    `tawreed`.
  - تُنقل دالة `append_cart_removal_summary` (التي تكتب CSV عبر
    `tawreed_artifacts`) إلى طبقة `tawreed` (مثلاً داخل `tawreed_artifacts.py`
    أو `tawreed_cart_removal_*`)، لأنها فعل جانبي (side effect) لا منطق أعمال.
  - يُحدَّث المستدعي `tawreed_cart_removal_core.py` ليستورد النموذج من `core`
    والكاتب من `tawreed`.
- **المطلوب لتنفيذها:** تتبع كل مستدعي لـ`append_cart_removal_summary`
  (`grep`)، نقل الدالة، تحديث الاستيرادات، تشغيل `test_cart_removal_items.py`
  و`test_tawreed_cart_removal.py`.
- **معيار النجاح:** لا استيراد `..tawreed` داخل أي ملف في `core` (تحقق بـgrep)؛
  الاختبارات المرتبطة تمر.

#### P0.3 — إزالة تسريب Playwright من مستوى الاستيراد في الاختبارات النقية
- **المشكلة:** استيراد `playwright` على مستوى الوحدة في `tawreed_api_main.py:8`
  يُسقط جمع 28 اختباراً عند غياب الحزمة، ويخلط طبقة integration بالوحدة النقية.
- **الحل (بدون تغيير سلوك):** التأكد أن الاختبارات النقية (core) لا تستورد
  `tawreed` إطلاقاً (هي كذلك أصلاً). توثيق أن اختبارات `tawreed` تتطلب بيئة
  بـplaywright مثبت. اختيارياً: تأجيل استيراد playwright إلى داخل الدالة
  (lazy import) في نقطة الدخول فقط إن لم يضر بالأداء — **يُسجَّل كقرار** ولا
  يُنفَّذ إن خالف نمط الكود الحالي.
- **معيار النجاح:** `pytest` على ملفات core يمر بلا أخطاء جمع؛ توثيق متطلب
  البيئة لاختبارات tawreed.

#### P0.4 — توحيد مصدر الإدخال المزدوج `input/` ↔ `data/input/`
- **المشكلة:** مجلدان متوازيان للإدخال يربكان الكود والمستخدم.
- **المطلوب:** تحديد المصدر المعتمد فعلياً في الكود (`grep` على `data/input`
  و`input/`)، توحيد المسار في `config.yaml`/`config_models.py`، توثيق المسار
  الموحَّد. **لا حذف لبيانات قبل تأكيد عدم الاستخدام.**
- **معيار النجاح:** مسار إدخال واحد معتمد ومُوثَّق؛ الاختبارات والأوامر تعمل.

---

### المرحلة P1 — توحيد الفتات في الطبقة عالية الخطر (Services/Core)

> الهدف: تقليص عدد ملفات `core` و`drug_matching` بدمج المجموعات المُفتَّتة
> في وحدات متماسكة موجَّهة بالميزة، مع إبقاء الواجهات العامة ثابتة.

> **نمط الدمج الموحَّد لكل مجموعة:**
> 1. اقرأ كل ملفات المجموعة وارسم اعتمادياتها الداخلية.
> 2. ادمجها في ملف/ملفين متماسكين (حسب الميزة، لا حسب عدد الأسطر).
> 3. أبقِ الواجهة العامة: حوِّل الملف القديم إلى re-export أو حدِّث المستوردين.
> 4. شغّل اختبارات المجموعة + `rule_audit.py`.
> 5. commit مستقل.

#### P1.1 — `ai_rotation_config_*` (الأسوأ: 11 ملفاً، متوسط 27 سطراً)
- **الإجراء:** دمج إعدادات كل مزوّدي AI في `ai_rotation_config.py` واحد عبر
  سجل (registry) من dataclasses بدل ملف لكل مزوّد.
- **اختبارات الحماية:** `test_ai_provider_cooldown.py`,
  `test_ai_decision_conflicts.py`.

#### P1.2 — `ai_rotation_*` العائلة الكاملة (20 ملفاً → ~3–4 ملفات)
- **الإجراء:** دمج `core/models/health/providers` للنظام في وحدات منطقية:
  `ai_rotation.py` (core+models), `ai_rotation_health.py` (health كاملاً),
  `ai_rotation_config.py` (من P1.1).
- **اختبارات الحماية:** اختبارات `test_ai_*` + `test_auto_refresh.py`.

#### P1.3 — `product_matching_*` (18 ملفاً → ~4–6 ملفات حسب المسؤولية)
- **الإجراء:** تجميع حسب المسؤولية: scoring (`_scoring/_token_scoring/
  _sequence_scoring`), decisions (`_decisions*`), identity/normalization,
  acceptance/orderable/safe_omission. دمج الفتات (16, 24, 25, 41 سطراً).
- **اختبارات الحماية:** `test_product_matching.py`, `test_match.py`,
  `test_matching_confidence.py`, `test_matching_risk.py`.
- **ملاحظة:** `tawreed` يستورد دوال خاصة (`_search_queries_for_item`) من هنا —
  تأكد من ثبات هذه الواجهة أو رفعها لواجهة عامة (يُسجَّل كقرار، لا تغيير سلوك).

#### P1.4 — `matching_*` (8 ملفات) + `matching_models`/الأنواع
- **الإجراء:** تجميع نماذج البيانات والأنواع المشتركة في وحدة types واضحة،
  ودمج `penalties/penalty_tokens` و`trace/trace_fields`.
- **اختبارات الحماية:** `test_matching_*`, `test_matching_trace.py`.

#### P1.5 — `manual_review_*` (13 ملفاً) + اتساق طبقة الـRepository
- **الإجراء:** دمج مجموعة `manual_review_store_*` (store+helpers+query+sql)
  في وحدة repository متماسكة؛ نقل نصوص SQL الخام
  (`store.py:116`, `store_helpers.py:47`) إلى `store_sql.py`؛ توحيد
  `upsert_batch` للمرور عبر طبقة `DatabaseQueries`.
- **اختبارات الحماية:** `test_manual_review_*` (corrections, hints, candidates,
  removal, runtime, selection).

#### P1.6 — `order_ai_*` (9) + `order_run_artifact_rows_*` (6)
- **الإجراء:** دمج فتات `order_run_artifact_rows_*` (ملفات 19/20/24 سطراً) في
  وحدة واحدة؛ تجميع `order_ai_*` حسب التدفق (flow/matching/verify/review).
- **اختبارات الحماية:** `test_order_ai_matching.py`,
  `test_order_ai_run_summary.py`, `test_order_run_artifacts.py`.

#### P1.7 — `trace_log_*` (19) + `verifier_*` (19) + `indexer_*` (12)
- **الإجراء:** هذه أكبر العائلات. تُدمج كل عائلة في 3–5 ملفات منطقية
  (مثلاً verifier: request/response/review/helpers بدل 19 ملفاً).
- **اختبارات الحماية:** `test_drug_matching_*`, `test_matching_logging.py`.
- **تحذير:** هذه الوحدات في `BASELINE_VIOLATIONS` (ملفات كبيرة سلفاً) — الدمج
  يجب ألا يزيد المخالفات؛ راجع `rule_audit.py` بعد كل دمج.

#### P1.8 — `prevented_items_*` (5) + `utils/excel_*` (5) + `pipeline_*` (11)
- **الإجراء:** دمج كل مجموعة في وحدة متماسكة (pipeline الأهم: 11 ملفاً،
  6 منها تحت 40 سطراً).
- **اختبارات الحماية:** `test_prevented_items.py`, `test_excel.py`,
  `test_chunking.py`, `test_drug_matching_*`.

---

### المرحلة P2 — توحيد طبقة Integration (`tawreed`)

> 114 ملفاً. الدمج هنا أكثر حساسية لأنها تلمس المتصفح والشبكة فعلياً.
> نفس نمط الدمج الموحَّد، مع اختبارات smoke حيثما توفرت بيئة playwright.

- **P2.1** `tawreed_api_*` (18 ملفاً → ~5): توحيد العائلة مع الإبقاء على
  فصل `_main`/`_flow`/`_payloads` المنطقي. اختبار: `test_tawreed_api*.py`.
- **P2.2** `tawreed_order_*` (13 ملفاً): دمج `tawreed_order_summary_*`
  (الفتات 21/22/50 سطراً) و`tawreed_order_flow_*`. اختبار:
  `test_order_run_artifacts.py`, `test_order_result_merger.py`.
- **P2.3** `tawreed_product_export_*` (8) + `tawreed_match_logs_*` (7) +
  `tawreed_products_flow_*` (6): دمج كل عائلة. اختبارات:
  `test_tawreed_product_export*.py`, `test_tawreed_match_logs.py`,
  `test_tawreed_products_flow.py`.
- **P2.4** `tawreed_session_*` (5) + `tawreed_cart_removal_*` (5) +
  `tawreed_dom_*`/`tawreed_auth_*`/`tawreed_bot_*`/`tawreed_summary_*`/
  `tawreed_match_only_*`/`tawreed_artifacts_*`: دمج العائلات الصغيرة.
  اختبارات: `test_tawreed_session.py`, `test_tawreed_cart_removal.py`,
  `test_tawreed_auth_waits.py`, `test_tawreed_bot.py`.
- **P2.5** نقل `core/utils/playwright_browser.py` إلى طبقة `tawreed` (أو
  طبقة infrastructure مخصّصة) لإزالة الوعي بالمتصفح من `core`.
  اختبار: `test_playwright_browser.py`.

---

### المرحلة P3 — توحيد طبقتي Transport (`cli` + `ui`)

- **P3.1** `cli_parser_*` (12 ملفاً، متوسط 41 → ملف/ملفين): دمج محلِّلات
  الوسائط الفرعية. اختبار: `test_cli_parser.py`.
- **P3.2** `cli_order_*` (11) + `cli_match_products_*` (5) + `item_worker_*`(3):
  دمج كل عائلة controller/command. اختبارات: `test_cli_commands.py`,
  `test_item_worker_*.py`.
- **P3.3** `streamlit_manual_review_*` (16 ملفاً → ~5): أكبر عائلة UI.
  دمج `_page_*` و`_page_saved_*` المُفتَّتة. اختبار:
  `test_streamlit_manual_review.py`.
- **P3.4** `streamlit_order_*` (7) + `streamlit_results_*` (5) +
  `streamlit_remove_cart_*` (4) + `streamlit_product_matching_*` (4):
  دمج كل عائلة. اختبارات: `test_streamlit_*`.

---

### المرحلة P4 — تنظيف الجذر والتوثيق (تجميل، خطورة منخفضة)

- **P4.1** نقل السكربتات السائبة إلى `tools/`:
  `add_avil_to_cockroachdb.py`, `create_test_avil.py`, `diagnose_avil.py`.
  (تحقق من عدم وجود استيراد لها من الكود الإنتاجي قبل النقل.)
- **P4.2** حذف/أرشفة المخرجات السائبة في الجذر:
  `output.json`, `output3.json`, `output_decision.json`,
  `login_test_result.txt`, `product_matching_functions.txt`,
  `test_avil_fix.xlsx`. (التحقق من `.gitignore` أولاً.)
- **P4.3** أرشفة تقارير `docs/*.md` القديمة (52 ملفاً) في `docs/archive/`
  مع إبقاء `project_guidelines.md`, `PROJECT_MAP.md`, `starting_prompt.md`,
  وهذه الخطة. (لا يمس الكود.)
- **P4.4** مزامنة `tools/rule_audit.py`: بعد التوحيد، تقليص قوائم
  `EXCEPTED_FILE_LENGTHS` و`BASELINE_VIOLATIONS` لتعكس الواقع الجديد
  (مصدر الحقيقة كما في `project_guidelines.md` §Source of Truth).

---

## 4. البنية المستهدفة (Target File Tree — مختصرة)

```
PharmaSupplyBot/
├─ run.py                      # CLI entrypoint (transport)
├─ streamlit_app.py            # GUI entrypoint (transport)
├─ config.yaml
├─ requirements.txt
├─ src/
│  ├─ cli/                     # 38 → ~12 ملفاً (transport + controllers)
│  │  ├─ cli_parser.py         # كل المحلِّلات الفرعية موحَّدة
│  │  ├─ cli_commands.py
│  │  ├─ cli_order.py          # عائلة الطلب موحَّدة
│  │  ├─ cli_match_products.py
│  │  └─ item_worker.py
│  ├─ ui/                      # 54 → ~20 ملفاً (presentation)
│  │  ├─ streamlit_main.py
│  │  ├─ streamlit_manual_review.py   # العائلة موحَّدة
│  │  ├─ streamlit_order.py
│  │  ├─ streamlit_results.py
│  │  └─ streamlit_remove_cart.py
│  ├─ tawreed/                 # 114 → ~40 ملفاً (integration)
│  │  ├─ tawreed_api.py
│  │  ├─ tawreed_order.py
│  │  ├─ tawreed_session.py
│  │  ├─ tawreed_products_flow.py
│  │  ├─ tawreed_cart_removal.py
│  │  ├─ tawreed_product_export.py
│  │  ├─ tawreed_artifacts.py
│  │  └─ playwright_browser.py # مُنقول من core/utils
│  └─ core/                    # 227 → ~90 ملفاً (business + data)
│     ├─ config/               # إعدادات مركزية
│     ├─ models.py             # الأنواع/الكيانات النقية المجمَّعة
│     ├─ product_matching.py   # العائلة موحَّدة
│     ├─ matching.py           # rules/risk/penalties/trace
│     ├─ prevented_items.py
│     ├─ cart_removal.py       # نموذج نقي فقط (بلا I/O من tawreed)
│     ├─ order_ai.py
│     ├─ manual_review.py
│     ├─ data/                 # طبقة Repository
│     │  ├─ database.py
│     │  └─ manual_review_store.py   # + store_sql موحَّد
│     └─ drug_matching/        # ~120 → ~30 ملفاً
│        ├─ normalizer.py
│        ├─ indexer.py
│        ├─ verifier.py
│        ├─ ai_rotation.py     # config+core+health موحَّد
│        ├─ ai_steps.py
│        ├─ trace_log.py       # العائلة موحَّدة
│        └─ pipeline.py
├─ tools/                      # + السكربتات المنقولة من الجذر
├─ tests/
└─ docs/
   ├─ project_guidelines.md
   ├─ ARCHITECTURE_REFACTOR_PLAN.md  (هذا الملف)
   └─ archive/                 # التقارير القديمة
```

**التقدير المستهدف:** من **434 ملفاً** إلى **~190–210 ملفاً** دون أي تغيير
سلوكي، مع رفع متوسط حجم الملف نحو نطاق صحي (60–100 سطر) وتقليل عدد ملفات
«تحت 50 سطراً» من 151 إلى أقل من ~25.

---

## 5. بوابات التحقق لكل مرحلة (Verification Gates)

| المرحلة | بوابة التحقق الإلزامية |
|---|---|
| كل خطوة | `python3 tools/rule_audit.py` ⇒ `rule_audit_ok` أو عدد أقل |
| P0.2 | `grep -rn "from ..tawreed" src/core/` ⇒ صفر نتيجة |
| P0.3 | `pytest tests/` على ملفات core بلا أخطاء جمع |
| P1.* | اختبارات المجموعة المرتبطة تمر (مذكورة بكل خطوة) |
| P2.* | اختبارات tawreed تمر (تتطلب playwright مثبتاً) |
| P3.* | اختبارات `test_cli_*` و`test_streamlit_*` تمر |
| نهائي | `pytest -q` كامل = نفس عدد النجاحات في P0.1 (لا Regression) |

---

## 6. تسلسل التنفيذ الموصى به (Milestones)

1. **M0:** P0.1 → P0.4 (تثبيت البيئة + كسر الحلقة + التسريب + توحيد الإدخال).
2. **M1:** P1.1 → P1.8 (توحيد core/drug_matching — أعلى عائد على الوضوح).
3. **M2:** P2.1 → P2.5 (توحيد tawreed).
4. **M3:** P3.1 → P3.4 (توحيد cli + ui).
5. **M4:** P4.1 → P4.4 (تنظيف + مزامنة أداة التدقيق).

كل Milestone يُختم بـ`pytest` كامل + `rule_audit.py` ومقارنة مع baseline P0.1.

---

## 7. ملاحظات/مشكلات مكتشفة (Discovered Notes/Issues — لا تُصلَح الآن)

> وفق القاعدة: «اكتشفتَ خللاً أثناء إعادة الهيكلة؟ سجِّله ولا تصلحه».

1. **بيئة الاختبار ناقصة:** `playwright` في `requirements.txt` لكنه غير مثبت
   محلياً ⇒ 28 خطأ جمع. ليس عيب كود بل بيئة. *قرار:* توثيق خطوة
   `playwright install` كمتطلب اختبار.
2. **حلقة استيراد core↔tawreed** (`cart_removal_summary.py:7`) — تُعالَج في P0.2.
3. **اتساق طبقة Repository:** `upsert_batch` يفتح cursor يدوياً
   (`manual_review_store.py:81-85`)، ونصوص SQL خام خارج `store_sql.py`
   (`store.py:116`, `store_helpers.py:47`). تحسين اتساق فقط (لا تغيير سلوك).
4. **حارس الأخطاء غير مُستخدم:** `streamlit_manual_review_data.py:16,65` يُنشئ
   `ManualReviewStore` مباشرة بدل `manual_review_store_or_stop()` ⇒ أخطاء DB
   قد لا تظهر برسالة Streamlit ودّية.
5. **استيراد دوال خاصة عبر الطبقات:** `tawreed` يستورد
   `_search_queries_for_item` (دالة خاصة) من `core.product_matching`
   (`tawreed_search_logic.py:17`, `tawreed_api_matching.py:12`) — اقتران هش.
6. **ازدواجية مجلدات الإدخال** `input/` vs `data/input/` — تُوحَّد في P0.4.
7. **تضخم التوثيق:** 52 تقرير `.md` متراكم في `docs/` — يُؤرشَف في P4.3.
8. **ملفات سائبة في الجذر** (سكربتات + JSON تشخيصي) — تُنقَل/تُحذَف في P4.

---

## 8. ما الذي لن تفعله هذه الخطة (Out of Scope)

- لا تغيير في خوارزميات المطابقة، التسعير، أو تدفق الطلب/الإزالة.
- لا ترقية تبعيات ولا تغيير لمحرك قاعدة البيانات.
- لا إضافة ميزات (متعدد اللغات، إلخ) — تلك بنود في `STATUS.md` خارج نطاق
  إعادة الهيكلة.
- لا حذف بيانات إدخال أو artifacts قبل تأكيد عدم الاستخدام.
```
