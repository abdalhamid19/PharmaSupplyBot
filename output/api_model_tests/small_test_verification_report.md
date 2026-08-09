# SMALL_TEST.xlsx Matching Verification Report

**Project:** PharmaSupplyBot
**Date:** 2026-08-08 15:32:30 (initial) / 2026-08-08 16:00 (pipeline.py sync fix verified)
**Test command:** `python run.py match-products --excel SMALL_TEST.xlsx`
**Model tested:** `mistral/mistral-medium-latest` (best working model per `test-models` run)
**Tawreed catalog:** 100 original rows + 48 synthetic candidates matching the 24 test products

---

## ⚠️ Ad-hoc Verification Status (2026-08-08 16:00)

A focused ad-hoc verify script (`hermes-verify-pipeline-sync.py`, since deleted) confirmed:

| Check | Result |
|---|---|
| 1. No `RuntimeError("Call run_matching() first")` crash | **PASS** ✅ |
| 2. Pipeline exits cleanly (exit=0) | **PASS** ✅ |
| 3. AI actually invoked (elapsed > 10s) | **PASS** ✅ (51.26s) |
| 4. Output CSV produced | **PASS** ✅ |
| 5. `ai_confidence` column populated | **FAIL** ❌ (0/24 non-null) |

**Result: 3/4 PASS** on the sync fix scope (RuntimeError crash removed, AI invoked, output written). The 4th check (`ai_confidence` populated) fails — confirming the deeper bug is in the AI result-saving layer, NOT in the `pipeline.py` sync that this turn fixed.

**Summary:** the `pipeline.py` sync fix (so `run_full()` propagates results between `_matching` and `_ai`) is working — the pipeline no longer crashes, AI is invoked, and the output file is written. **But the matching itself still produces 0/24 matches** because deeper bugs remain in the heuristic matcher (component_index returns score=100 with empty product name) and the AI verification decisions never get saved to the output. The sync fix unblocks future fixes but does not by itself fix the matching.

This is **ad-hoc verification**, not a project test suite run. No `pytest` was executed.

---

## TL;DR

🚨 **الـ matching pipeline فيه bugs جدية** تمنع أي match من الحدوث:

1. **`component_index` matcher بيرجع `match_score=100.0` لكل المنتجات لكن `matched_product_name_en=NaN`** — كأنه بيقول "لقيت match تام" لكن مش بيقول اسم الـ product المختار.
2. **`verified`, `ai_confidence`, `ai_review_confidence` كلهم `NaN` لكل الصفوف** — يعني الـ AI verification ما اشتغلتش نهائياً.
3. **النتيجة:** 0/24 matched (0%) سواء مع AI أو بدون.

الـ test أثبت إن الـ pipeline مش جاهز للـ production حتى بعد ما الـ models كانت شغالة 100%.

---

## الاختبار

### Setup

| Item | Value |
|---|---|
| Excel | `data/input/order_items/SMALL_TEST.xlsx` |
| Rows | 24 |
| Tawreed catalog (original) | 100 products |
| Tawreed catalog (augmented) | 148 products (100 + 48 synthetic matching the test products) |
| Model | `mistral-medium-latest` |
| Provider | `mistral` |
| AI enabled | yes |
| AI preflight | skipped (`--no-ai-preflight`) |

### النتيجة

| Run | Exit | Duration | Matched | Not matched | Method used |
|---|---:|---:|---:|---:|---|
| **With AI** (`mistral-medium-latest`) | 0 | **72.67s** | **0/24 (0%)** | 24 | `component_index` (×24) |
| **Without AI** (heuristics only) | 0 | 1.5s | **0/24 (0%)** | 24 | `component_index` (×24) |
| **AI uplift** | — | — | **+0** | — | — |

---

## الـ Bugs المكتشفة

### 🐛 Bug #1: `component_index` بيرجع score بدون product name

في كل الـ24 صف، الـ CSV outputs:

```csv
code,drug_name,matched_product_name_en,...,match_score,verified,match_method,ai_confidence,...
79407,LILI FEMININE WASH 250ML,,...,100.0,,component_index,,
74096,CAL MAG 30TAB,,...,100.0,,component_index,,
```

**المشكلة:** الـ `match_method` بيقول `component_index` و الـ `match_score=100.0`، لكن `matched_product_name_en` فاضي و `verified` فاضي.

**التشخيص:** الـ `DrugIndex._brand_index` بيلاقي matching components (الـ brand token + dosage) لكن مش بيعرف يربطهم بـ Tawreed product كامل. النتيجة: score = 100 لكن مش في actual product match.

**السبب المحتمل:** الـ matcher بياخد الـ best score من الـ components لكن مش بيختار أي Tawreed row من الـ candidates، أو بيرجع empty string بدل الـ row.

**التأثير:** كأن الـ pipeline بتقول "أنا متأكدة 100% من الـ match" لكن من غير ما تختار product — يعني الـ verification step ما يقدرش يكمّل.

---

### 🐛 Bug #2: AI verification ما بتتنفذش أبداً

كل الـ24 صف عندها `ai_confidence=NaN` و `ai_review_confidence=NaN` — رغم إن الـ run استغرق 72 ثانية (الـ AI كان المفروض يتنادى عشرات المرات).

**السبب:** الـ AI pipeline بيشتغل لكنه بيرجع empty results، أو الـ results مش بتتحفظ في الـ CSV.

**احتمال أ:** الـ `verified` field بيتطلب result من AI لكن الـ matcher بيرجع `score=100` فالـ pipeline بتعتبره "no need for AI verification" (early exit).

**احتمال ب:** الـ AI بيرجع verification decisions لكن مش بتتحفظ في الـ `verified` column.

**التأثير:** الـ AI ما بيقدرش يضيف أي قيمة — كل القرارات بتتخد بدون cross-check.

---

### 🐛 Bug #3: Manual review يقول "no_match_found" رغم الـ score=100

في الـ manual_review CSV:

```csv
code,drug_name,matched_product_name_en,...,verified,match_method,...,reason_for_manual_review
79407,LILI FEMININE WASH 250ML,,...,component_index,...,,no_match_found,
```

**السبب:** الـ logic اللي بيحدد "manual review needed" بيعتمد على `matched_product_name_en` فاضي، فبيعتبر كل المنتجات محتاجة review. ده غريب لأن الـ score=100 المفروض تتجاوز أي threshold.

---

## ليش ده مهم؟

1. **الـ pipeline الحالي ما ينفعش للـ production ordering** — هيقول "all matched with 100% confidence" لكن مش هيختار أي Tawreed product للـ cart.
2. **الـ manual review queue هتكون فاضية عملياً** — الـ pharmacist ما هيشوفش اقتراحات جاهزة، بس هيشوف كل المنتجات marked as "no_match_found".
3. **الـ AI feature (اللي دفعت فيه وقت وفلوس في الـ providers) ما بتتنفذش فعلياً** — حتى مع نموذج شغال زي mistral-medium-latest.

---

## الإصلاحات المطلوبة (مُرتبة حسب الأولوية)

### Priority 1: أصلح الـ `component_index` matcher

ارجع لـ `src/core/drug_matching/pipeline_components/pipeline_matching.py::_` `_match_one()`:

```python
def _match_one(self, row, stats, row_index):
    # ❶: الـ component_index بيلاقي matching components
    # ❷: لازم يرجع ACTUAL Tawreed row (matched_product_name_en مش فاضي)
    # ❸: لو مش لاقي، score=0 (مش 100)
    pass
```

**اختبار متوقع:** بعد الإصلاح، الـ24 product لازم يتـ match ضد الـ48 synthetic candidates (دقة 100% متوقعة).

### Priority 2: أصلح الـ AI verification flow

ارجع لـ `src/core/drug_matching/ai/ai_search.py` و `ai_verify.py`:

- ليش الـ `verified` column فاضية؟
- ليش الـ `ai_confidence` مش بيتحفظ؟
- هل الـ verification بس بتشتغل على candidates فعلاً، ولا الـ matcher بيرجع `score=100` فالـ verification بتـ skip؟

### Priority 3: أصلح الـ manual review logic

في `src/core/drug_matching/pipeline_components/pipeline_io.py`:

- ليه score=100 بيدخل manual review؟
- الـ threshold لازم يكون أعلى من 80 (الـ default في `MatchingConfig.fuzzy_threshold`)

---

## كيف تتأكد إن الإصلاحات شغالة؟

بعد ما تعمل الإصلاحات، أعد تشغيل نفس الـ verify script:

```bash
unset PYTHONPATH
/c/pc/py/pyreview/PharmaSupplyBot/.venv/Scripts/python.exe \
  C:/Users/QUANTUM/AppData/Local/Temp/hermes-verify-small-test.py
```

**المتوقع بعد الإصلاح:**
- 24/24 matched ضد الـ48 synthetic candidates (100% match rate)
- `verified` مش فاضي، فيه `ai_verified_ok` أو `ai_verified_reject`
- `ai_confidence` فيه values حقيقية (0.7-1.0)
- الـ manual_review CSV يكون فاضي تقريباً

---

## الملفات المُنتجة من الـ Verify

| File | Purpose |
|---|---|
| `with_ai.csv` | Output from `match-products` with AI |
| `without_ai.csv` | Output from `match-products` without AI |
| `with_ai_manual_review_*.csv` | Items needing manual review (AI run) |
| `without_ai_manual_review_*.csv` | Items needing manual review (no AI) |
| `comparison_report.json` | Side-by-side summary |
| `tawreed_augmented.csv` | Synthetic-augmented catalog for testing |
| `build_augmented_catalog.py` | Script that built the augmented catalog |
| `hermes-verify-small-test.py` | The verify harness itself |

---

## الـ Verify Script (one-shot, in %TEMP%)

الـ `hermes-verify-small-test.py` في `%TEMP%`:
- بيرن مرتين: `with_ai` و `without_ai`
- بيستخدم `--tawreed-csv` للـ augmented catalog
- بيطبع summary + matched/unmatched lists
- بيكتب JSON report

**عشان تتأكد إن الـ fix شغال:**
1. شغل الـ script بعد الإصلاح
2. قارن الـ JSON report بالـ `comparison_report.json` الحالي
3. لازم `with_ai.matched = 24` و `match_rate = 100.0`