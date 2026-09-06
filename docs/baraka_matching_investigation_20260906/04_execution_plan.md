# Baraka Companies Safe Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** منع التطابقات الخاطئة في Arabic-only Excel targets مع الحفاظ على التطابقات ذات الهوية المثبتة.

**Architecture:** يعاد توصيل production matcher بعقد thresholds الموحد، ثم يضاف policy مصدره Excel: الاسم العربي الخام لا يصبح دليل English identity. الصف يمر فقط عند هوية bilingual موثقة أو قرار يدوي محدد، وبعدها تطبق form/strength/pack rules.

**Tech Stack:** Python 3.11، pytest، openpyxl، rapidfuzz، SQLite translation cache.

**Spec:** `docs/baraka_matching_investigation_20260906/01_reproduction_and_evidence.md`، `02_hypotheses_and_scores.md`، `03_solution_options.md`.

## Global Constraints

- لا تغيّر Tawreed API إلا باختبار regression يثبت حاجة مشتركة.
- لا تستدع Cohere live من matcher أو trace loop.
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
- [x] commit: `fix: honor matching thresholds in diagnostic acceptance`.

### Task 2: إثبات هوية الصف العربي قبل القبول

**Files:** Modify `src/core/excel_target/excel_target_loader.py`, `src/core/excel_target/excel_target_matching.py`, `src/core/matching/product_matching_acceptance.py`; test both files under `tests/diagnostics/`.

**Interface:** consumes `TargetProduct.name`, dictionary/cache bilingual result، وmanual decision؛ produces `verified_brand_identity: bool` و`identity_evidence: str` على candidate.

- [x] شغّل H2 وscorecard. المتوقع أن H2 وprecision gate يفشلان، بينما exact-English وdeterminism ينجحان.
- [x] افصل الاسم الخام عن الاسم الإنجليزي الموثوق. Arabic-only row يحتفظ باسم raw Arabic ولا يكتب في `productNameEn` كأنه مصدر English. dictionary/cache/approved manual decision فقط تضيف evidence موثوقًا.
- [x] قبل threshold acceptance طبّق القاعدة: إذا كان `candidate["excelTarget"]` صحيحًا و`verified_brand_identity` غير صحيح، يرجع `(False, "", "Arabic-only candidate lacks verified brand identity")`. لا تطبق ذلك على Tawreed، ولا تعتبر shared numeric/form token دليل brand.
- [x] شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\diagnostics\test_baraka_matching_hypotheses.py tests\diagnostics\test_baraka_solution_scorecard.py tests\core\excel_target\test_excel_target.py tests\test_product_matching.py`. المتوقع كله PASS.
- [x] commit: `fix: require verified identity for Arabic excel candidates`.

### Task 3: جعل cache-only bilingual evidence قابلًا للقرار

**Files:** Modify `src/core/excel_target/excel_target_matching.py`; عند الحاجة فقط `src/core/normalization/bilingual_brand_matcher.py`; add focused fixture tests under `tests/core/excel_target/`.

**Interface:** consumes dictionary hit و`ar_to_en_cached_only` فقط؛ produces verified identity عندما brand similarity وحدها تتجاوز الحد، ثم compatibility validation.

- [x] أضف fixture: `اينوديب 30 كبسول` ينجح فقط عندما fixture يثبت brand `INODEP`؛ سالبوفنت يظل no-results حتى لو شارك `30`.
- [x] لا تستدع `ar_to_en`; cache miss تعني no-results أو manual review بسبب واضح، لا network fallback.
- [x] شغّل scorecard واختبارات Excel target. المتوقع PASS.
- [x] commit: `feat: verify Arabic excel matches from offline bilingual evidence`.

### Task 4: Replay وقرار الإنتاج

**Files:** Create artifact summary جديد من replay فقط؛ Modify `docs/baraka_matching_investigation_20260906/05_verification_protocol.md` بنتائج فعلية فقط.

- [x] شغّل `.\.venv\Scripts\python.exe -m pytest -q`. المتوقع 0 failed.
- [x] شغّل replay Excel-only لأول 50 بلا Tawreed profile أو browser أو network، واحفظ summary منفصلًا.
- [x] راجع كل `matched-only`: يجب وجود `identity_evidence`، وتوافق strength/form/pack، ولا يوجد `No extra numeric tokens` كسبب وحيد.
- [x] بعد نجاح replay فقط شغّل الأمر الأصلي في `--match-only`; لا cart mutation.
- [x] commit تقرير التحقق: `docs: record Baraka matching verification`.

## مراجعة الخطة

- H1: Task 1.
- H2/H3: Task 2.
- bilingual correctness بدون شبكة: Task 3.
- regression وreplay والأمر الأصلي: Task 4.
- كل checkboxes فارغة؛ هذه الخطة لم تنفذ انتظارًا للموافقة.

