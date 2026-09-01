# 01 — خريطة التبعيات الكاملة (Analysis)

> تحقق من كل سطر ومسار مذكور هنا قبل البدء. آخر تحديث: 2026-09-01.

## 1. الصورة الكبيرة: نظاما matching منفصلان

| | Standalone Matching (سيُحذف) | Matching الداخلي في Order (ممنوع المساس) |
|---|---|---|
| **CLI** | `py run.py match-products` | `py run.py order` |
| **كود الأمر** | `src/cli/commands/cli_match_products.py` | `src/cli/commands/cli_order.py` + `src/tawreed/` |
| **GUI** | تاب "Product Matching" | تاب Order |
| **ملف الـ GUI** | `src/ui/views/streamlit_product_matching.py` | `src/ui/order/streamlit_order.py` |
| **المحرك** | `src/core/drug_matching/` (الجزء غير المشترك) | `src/core/matching/` + `src/core/matching_types.py` + `src/tawreed/matching/` |

**القاعدة الذهبية:** `order` لا يستدعي `cli_match_products.py` ولا `MatchPipeline` إطلاقًا. الاستخدام الوحيد لـ `MatchPipeline` في `src/` هو من داخل `cli_match_products.py:17` نفسه.

## 2. تفصيل `src/core/drug_matching/` — مصير كل جزء

| الجزء | الملفات | المصير | السبب |
|---|---|---|---|
| `normalization/` | 19 ملف `.py` | **نقل** إلى `src/core/normalization/` | يستخدمها `order` (انظر §3) |
| `config/` | 4 ملفات | **حذف** | `MatchingConfig` المستخدم في الـ config العام تأتي من `src/core/config/config_models.py:39` وليس من هنا. `setup_logging` لا يستخدمها أحد خارج الحزمة (تم التحقق بـ rg) |
| `indexing/` | 14 ملف | **حذف** | حكر على MatchPipeline (يستوردها `pipeline.py` فقط) |
| `tracing/` | 7 ملفات | **حذف** | يستوردها `cli_match_products.py:18` و`pipeline_components/` فقط |
| `pipeline_components/` | 3 ملفات | **حذف** | حكر على pipeline |
| `pipeline.py` | 1 ملف | **حذف** | نقطة الدخول الخاصة بـ match-products |
| `pricing.py` | 1 ملف | **نقل** إلى `src/core/normalization/` أو تركه بجانب indexing | المستوردون الوحيدون: `indexing/indexer_build.py:9` و `indexing/indexer_detailed_lookup.py:6` — كلاهما سيُحذف. لو احتاجه المستقبل، يُنقل مع normalization |
| `ai/` | 0 ملفات `.py` (pycache فقط) | **حذف مجاني** | فارغة تمامًا — بقايا `.pyc` قديمة |
| `verification/` | 0 ملفات `.py` (pycache فقط) | **حذف مجاني** | فارغة تمامًا |
| `__init__.py` | 1 ملف | **حذف** | يصدّر من `.config` التي ستُحذف |

## 3. مستوردو `normalization/` من خارج الحزمة (يجب إعادة توجيههم)

### 3.1 كود الإنتاج (6 مواضع — كلها مرتبطة بـ order أو بالـ identity)

| الملف:السطر | الاستيراد | يعتمد عليه order؟ |
|---|---|---|
| `src/core/matching/search_query_templates.py:5` | `parse_drug` | ✅ نعم (توليد استعلامات البحث) |
| `src/core/matching/matching_confidence.py:7` | `components_match, parse_drug` | ✅ نعم |
| `src/core/matching/matching_risk.py:39` | `parse_drug` (داخل دالة — lazy) | ✅ نعم (سياسة `--matching-risk-policy`) |
| `src/core/matching/product_matching_acceptance.py:10` | `components_match, parse_drug` | ✅ نعم |
| `src/core/matching/product_matching_numeric.py:8` | `components_match, parse_drug` | ⚠️ الاستيراد معطوب أصلًا: `from .drug_matching.normalization...` — الملف **غير مستورد من أي مكان** (verified dead code). يُصلح المسار أثناء النقل أو يُحذف (قرار منفصل) |
| `src/core/identity/manufacturer_identity.py:24` | `normalizer_manufacturer_extraction` | ✅ نعم (order يمر عبر identity) |

### 3.2 ملاحظة تبعية عكسية داخل normalization

`normalization/normalizer_matching_brand.py:15` يستورد من `src/core/identity/manufacturer_identity` (لازم استيراد — لتجنب الدائرية). بعد النقل، المسار يبقى صحيحًا لأنه absolute (`from ...identity...` يصبح بحاجة للمراجعة بعد تغيير عمق الحزمة — انظر Task 2 في الخطة).

### 3.3 الاختبارات المستوردة لـ normalization (تحتاج إعادة توجيه)

- `tests/core/drug_matching/test_drug_matching_normalizer.py` — يستورد من `normalization` + `indexing` (الجزء الخاص بـ indexing يُحذف، والملف يُنقل ويُفصل)
- `tests/solutions/test_s1_reject_co_prefix_brand.py:10-12`
- `tests/solutions/test_s2_raise_containment_threshold.py:13-14`
- `tests/solutions/test_s3_manual_review_only_insufficient.py:11-12`
- `tests/hypotheses/test_h1_brand_containment_co_prefix.py:13-14`
- `tests/hypotheses/test_h3_safe_omission_and_form_ok.py:11-12`
- `tests/hypotheses/test_h4_drops_already_rejected.py:11-12`
- `tests/test_co_avazir_mismatch.py:15-16`
- `tests/test_latest_no_results_regressions.py:190`

## 4. واجهة CLI — ما يُمس

| الملف | التعديل |
|---|---|
| `src/cli/cli_commands.py:8,14` | إزالة استيراد وإدخال `run_match_products_command` |
| `src/cli/typer_app.py:251-277` | حذف دالة `match_products_cmd` كاملة |
| `src/cli/typer_app.py:4` | تحديث docstring |
| `src/cli/commands/cli_match_products.py` | **حذف الملف** |
| `src/cli/commands/__init__.py:6` | تحديث التعليق |
| `src/cli/registry.py` | لا تعديل — التسجيل يتم بديكوريتور `@register`، وبحذف الملف يختفي الأمر تلقائيًا. الاختبار `tests/cli/test_registry.py:65` يُعدّل |

## 5. واجهة GUI — ما يُمس

| الملف:السطر | التعديل |
|---|---|
| `src/ui/streamlit_main.py:13` | حذف الاستيراد |
| `src/ui/streamlit_main.py:85-97` | حذف `matching_tab` من unpack + from-block |
| `src/ui/streamlit_main.py:110-116` | حذف `"Product Matching"` من `_main_tab_labels()` |
| `src/ui/views/streamlit_product_matching.py` | **حذف الملف كاملًا** (195 سطر) |
| `src/ui/views/__init__.py:7` | تحديث docstring |
| `src/ui/views/streamlit_results.py:29` | حذف `"match-products"` من قائمة `command_options()` |
| `src/ui/views/streamlit_timing.py:26` | لا تعديل — يقرأ من نتائج order (match-only elapsed) وليس من match-products |
| `src/ui/manual_review/streamlit_manual_review_page_saved.py:164` | تغيير المسار الوهمي `ARTIFACTS_DIR / "match-products" / "manual_research"` إلى اسم آخر (مثل `order/manual_research`) — الوظيفة نفسها تستخدم `order --match-only` (verified في `streamlit_manual_review_cli.py:78-83`) |

## 6. أدوات (tools/) ووثائق وملفات أخرى

| الملف | التعديل |
|---|---|
| `tools/update_baseline.py:30` | إزالة السطر |
| `tools/rule_audit.py:33,83-84` | إزالة الإدخالات |
| `tools/phase_validation.py:46-60` | حذف خطوة `match-products --help` وملف الـ CSV المرجعي |
| `tools/migrate_artifacts.py:11` | مراجعة (قد تُترك لو كانت أداة ترحيل تاريخية) |
| `README.md:56` | حذف قسم مثال match-products |
| `docs/cli_properties.html` | قسم `أمر match-products` (السطور ~169-195) |
| `docs/product_matching_mode.md` | ينقل إلى archive أو يُحذف مع إشارة في README |
| `docs/PROJECT_MAP.md` | مراجع متعددة (47, 235, 237, 288, 300, 315-316, 346, 352-353, 384, 401-402) |
| `docs/audit_logging.md:20,70-71` | مراجع لملف cli_match_products |
| `config.yaml` / `config.example.yaml` | قسم `matching:` **يبقى** — يخص MatchingConfig العام الذي يستخدمه order |
| `artifacts/match-products/` | أرشيف قديم — يبقى على القرص (قرارك: إزالة من قائمة Results فقط) |

## 7. الاختبارات — خطة التعامل

| الملف | القرار |
|---|---|
| `tests/cli/test_typer_app_match.py` | **حذف** كامل |
| `tests/ui/views/test_streamlit_product_matching.py` | **حذف** كامل |
| `tests/cli/test_typer_app_compat.py:360-380` | حذف بلوك match-products فقط |
| `tests/cli/test_summary.py:251` | إزالة من tuple |
| `tests/cli/test_registry.py:65` | إزالة من expected set |
| `tests/cli/test_shortcuts.py:53-58, 91-98` | حذف الاختبارين |
| `tests/cli/test_run_logging_e2e.py:99,109` | حذف السطرين من قائمة الحالات |
| `tests/core/drug_matching/test_drug_matching_indexer.py` | **حذف** (indexing محذوف) |
| `tests/core/drug_matching/test_drug_matching_normalizer.py` | **نقل** إلى `tests/core/normalization/` + تحديث imports |
| `tests/core/matching/test_logging_integration.py` | يعتمد على `drug_matching.config.config_helpers.setup_logging` — يُعدل أو يُحذف الجزء الخاص (setup_logging ستُحذف مع config/) |
| `tests/core/test_logging_audit.py:187,209` | إزالة إدخالات `src.core.drug_matching` |
| اختبارات solutions/hypotheses (§3.3) | إعادة توجيه imports فقط |

## 8. ما يُمنع مساسه نهائيًا (قائمة التحقق الحمراء)

- [ ] `src/core/matching/` — كل الملفات (order engine)
- [ ] `src/core/matching_types.py`
- [ ] `src/core/config/` — خاصة `MatchingConfig` في `config_models.py:39` و `config_factory.py:95` (order يقرأ قسم `matching:` من config.yaml)
- [ ] `src/tawreed/` — كل شيء بما فيها `matching/` و `--match-only`
- [ ] `src/ui/manual_review/` — الوظيفة (فقط السطر 164 يُعدل)
- [ ] `src/core/database/` — order_runs_* تستخدم `candidate_identity` من matching
- [ ] `src/core/identity/manufacturer_identity.py` — فقط استيراده لـ normalization يُعاد توجيهه
- [ ] `src/cli/commands/cli_order*.py` و `item_worker.py`
- [ ] قسم `matching:` في config.yaml
