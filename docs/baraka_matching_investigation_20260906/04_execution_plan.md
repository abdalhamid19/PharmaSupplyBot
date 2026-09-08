# Baraka Companies Safe Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** منع التطابقات الخاطئة في Arabic-only Excel targets مع الحفاظ على التطابقات ذات الهوية المثبتة.

**Architecture:** يعاد توصيل production matcher بعقد thresholds الموحد، ثم يضاف policy مصدره Excel: الاسم العربي الخام لا يصبح دليل English identity. الصف يمر فقط عند هوية bilingual موثقة أو قرار يدوي محدد، وبعدها تطبق form/strength/pack rules. يمكن استخدام `tawreed_products.csv` كـalias محلي للهوية فقط إذا رُبط الاسم العربي بصف موجود فعلياً في Baraka؛ لا يستخدم الملف ككتالوج أو مصدر سعر/توافر.

**Tech Stack:** Python 3.11، pytest، openpyxl، rapidfuzz، SQLite translation cache.

**Spec:** `docs/baraka_matching_investigation_20260906/01_reproduction_and_evidence.md`، `02_hypotheses_and_scores.md`، `03_solution_options.md`.

## Global Constraints

- لا تغيّر Tawreed API إلا باختبار regression يثبت حاجة مشتركة.
- لا تستدع Cohere live من matcher أو trace loop.
- تحميل `tawreed_products.csv` محلي ومرة واحدة لكل فهرس/session مسموح، لكن لا توجد مكالمة API أو fuzzy Tawreed داخل حلقة العناصر.
- لا تحوّل safety tests إلى `xfail` ولا تغيّر expected false candidate.
- لا تشغّل submit/cart؛ integration يكون `--match-only` فقط.
- كل commit صغير، وكل task ينتهي باختبار محدد.

---

### Task 1: تثبيت عقد القبول الموحد

**Files:** Modify `src/core/matching/product_matching_acceptance.py`; test `tests/diagnostics/test_baraka_matching_hypotheses.py` and `tests/test_product_matching.py`.

**Interface:** consumes `acceptance_details(query, candidate, score, matching_config, helpers)` from `src/core/matching/matching_rules.py`; produces `_diagnostic_acceptance(...) -> tuple[bool, str, str]` that rejects a candidate not meeting thresholds.

- [x] شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\diagnostics\test_baraka_matching_hypotheses.py::TestBarakaMatchingHypotheses::test_h1_production_matcher_must_honor_the_threshold_contract`. المتوقع FAIL لأن سالبوفنت مقبول.
- [x] بعد `_check_rejections`، استدع `acceptance_details` بدل قبول `_numeric_acceptance` وحده. مرر helpers بالترتيب: `_normalize_text`, `_candidate_english_name`, `_best_candidate_overlap`, `_numeric_match_count`. لا تلغِ hard rejections.
- [x] شغّل H1 مع `tests/test_product_matching.py`. المتوقع PASS.
- [x] سُجل تغيير threshold في worktree؛ لا يوجد ادعاء بوجود commit دون hash قابل للتحقق.

### Task 2: إثبات هوية الصف العربي قبل القبول

**Files:** Modify `src/core/excel_target/excel_target_loader.py`, `src/core/excel_target/excel_target_matching.py`, `src/core/matching/product_matching_acceptance.py`; test both files under `tests/diagnostics/`.

**Interface:** consumes `TargetProduct.name_ar` و`name_en` الموثوق وdictionary/cache/Tawreed alias/manual decision؛ produces `IdentityEvidence` typed على حدود القرار ثم حقول CSV عند الإخراج.

- [x] شغّل H2 وscorecard. المتوقع أن H2 وprecision gate يفشلان، بينما exact-English وdeterminism ينجحان.
- [x] افصل الاسم الخام عن الاسم الإنجليزي الموثوق. Arabic-only row يحتفظ باسم raw Arabic ولا يكتب في `productNameEn` كأنه مصدر English. dictionary/cache/approved manual decision فقط تضيف evidence موثوقًا.
- [x] قبل threshold acceptance طبّق القاعدة: إذا كان `candidate["excelTarget"]` صحيحًا و`verified_brand_identity` غير صحيح، يرجع `(False, "", "Arabic-only candidate lacks verified brand identity")`. لا يعتبر صف Tawreed مرشحاً؛ alias Tawreed المربوط بصف Baraka يدخل كـ`IdentityEvidence(kind="tawreed_catalog")` ثم يمر بنفس فحص التوافق، ولا تعتبر shared numeric/form token دليل brand.
- [x] شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\diagnostics\test_baraka_matching_hypotheses.py tests\diagnostics\test_baraka_solution_scorecard.py tests\core\excel_target\test_excel_target.py tests\test_product_matching.py`. المتوقع كله PASS.
- [x] سُجل تغيير الهوية في worktree؛ لا يوجد ادعاء بوجود commit دون hash قابل للتحقق.

### Task 3: جعل bilingual evidence offline قابلاً للقرار

**Files:** Modify `src/core/excel_target/excel_target_matching.py` و`src/core/excel_target/excel_target_identity.py`; عند الحاجة فقط `src/core/normalization/bilingual_brand_matcher.py`; add focused fixture tests under `tests/core/excel_target/`.

**Interface:** consumes exact dictionary hit أو cached translation أو local Tawreed alias أو native English؛ produces verified identity ثم compatibility validation. لا fuzzy brand ولا translation network fallback.

- [x] أضف fixture: `اينوديب 30 كبسول` ينجح فقط عندما fixture يثبت brand `INODEP`؛ سالبوفنت يظل no-results حتى لو شارك `30`.
- [x] لا تستدع `ar_to_en`; cache miss تعني no-results أو manual review بسبب واضح، لا network fallback.
- [x] أضف Tawreed alias بحيث يعيد `TargetProduct` من Baraka فقط، ويحافظ على كل variants قبل فحص form/strength/pack.
- [x] قِس أن `load_tawreed_catalog()` و`ar_to_en_many_cached_only()` ينفذان عند بناء الفهرس مرة واحدة، لا مرة لكل item؛ الاختبار والـbenchmark محفوظان في artifacts.
- [x] شغّل scorecard واختبارات Excel target. المتوقع PASS.
- [x] وثّق التغيير في تقرير التنفيذ؛ لا تفترض وجود git commit ما لم يظهر hash فعلي.

### Task 4: Replay وقرار الإنتاج

**Files:** Create artifact summary جديد من replay فقط؛ Modify `docs/baraka_matching_investigation_20260906/05_verification_protocol.md` بنتائج فعلية فقط.

- [x] شغّل بوابة Baraka المركزة؛ آخر تشغيل `87 passed, 8 subtests passed in 27.41s`.
- [x] شغّل `pytest -q tests` للتشخيص فقط؛ آخر نتيجة `21 failed, 974 passed, 19 skipped, 8 warnings, 134 subtests passed`. هذه failures خارج نطاق Baraka/Excel-target ولا يجوز إخفاؤها أو إعلان suite كاملة خضراء.
- [x] شغّل replay Excel-only لأول 50 بلا Tawreed profile أو browser أو network، واحفظ summary منفصلًا.
- [x] راجع كل `matched-only`: يجب وجود `identity_evidence`، وتوافق strength/form/pack، ولا يوجد `No extra numeric tokens` كسبب وحيد. في replay الأخير: 13 matches متوافقة و37 no-results؛ منها 29 identity missing و8 variant/compatibility rejection.
- [x] بعد نجاح replay فقط شغّل الأمر الأصلي في `--match-only`; لا cart mutation.
- [x] احفظ summary وJSONL ووقت التنفيذ، وسجّل commit hash فقط إذا تم إنشاؤه فعلياً.

## حالة الخطة بعد التنفيذ

- H1: Task 1 مكتملة ومغطاة بالاختبارات.
- H2/H3: Task 2 مكتملة؛ هوية الصف العربي منفصلة عن الاسم الخام.
- bilingual correctness بدون شبكة: Task 3 مكتملة؛ أضيفت اختبارات التطبيع وتقرير coverage وقياس بناء الفهرس مرة واحدة.
- regression وreplay والأمر الأصلي: Task 4 مكتملة مع تسجيل failures العامة خارج النطاق.
- الخطوات التالية غير المنفذة هي pre-translation بموافقة تشغيلية ومراجعة aliases اليدوية؛ لا تُخلط مع إصلاح false positives المنفذ.
