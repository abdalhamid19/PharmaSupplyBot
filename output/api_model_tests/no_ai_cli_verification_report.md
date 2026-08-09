# `--no-ai` CLI Baseline Verification Report

**Project:** PharmaSupplyBot
**Date:** 2026-08-08 (ad-hoc verify)
**Test command:** `python run.py match-products --no-ai --excel SMALL_TEST.xlsx`
**Input:** `data/input/order_items/SMALL_TEST.xlsx` (24 products)
**Models involved:** none (heuristic-only path)

---

## TL;DR

🚨 **`--no-ai` فيه bugs واضحة** — الـ CLI بيشتغل من غير crash، لكن الـ matcher مش بيلاقي أي product حتى لما الـ Tawreed catalog فيه exact synthetic matches جاهزة.

| Run | Catalog | Exit | Time | Matched | Status |
|---|---|---:|---:|---:|---|
| 1 | Real catalog (100 rows) | 0 | 1.84s | **0/24 (0%)** | كل المنتجات `match_method=no_match` |
| 2 | Augmented catalog (148 rows, exact synthetic matches) | 0 | 1.69s | **0/24 (0%)** | كل المنتجات `match_method=component_index` لكن **مفيش اسم** |

**اللي بيشتغل:**
- ✅ CLI بياخد الـ args صح
- ✅ بيشتغل بسرعة (~1.7s)
- ✅ بيخرج CSV بـ10 columns (correct schema)
- ✅ مفيش errors أو warnings في الـ logs

**اللي مش بيشتغل:**
- ❌ الـ heuristic بيرجع `score=100` لـ24 product لكن **من غير ما يختار اسم product واحد**
- ❌ على الـ real catalog: كل حاجة `no_match` — يعني مش بيلاقي حتى الـ brand token
- ❌ على الـ augmented catalog: بيلاقي "component" لكن مش بيربطه بـ Tawreed row فعلي

---

## الـ Setup

- **Python venv:** `C:\pc\py\pyreview\PharmaSupplyBot\.venv\Scripts\python.exe` (openpyxl, rapidfuzz, pandas, aiohttp all installed)
- **PYTHONPATH:** unset (prevented the Hermes-leak that hides missing deps)
- **Excel input:** 24 rows with columns `code, drug_name, qty, total_sales, ...`
- **Tawreed catalog (real):** 100 rows from `artifacts/export-products/wardany/20260722_1313/tawreed_products_20260722_1313.csv`
- **Tawreed catalog (augmented):** 148 rows = 100 real + 48 synthetic (exact + variant match per test product)

---

## Run 1: Real Catalog (100 rows)

| Metric | Value |
|---|---|
| Exit code | 0 |
| Elapsed | 1.84s |
| Total products | 24 |
| Matched | **0** |
| `match_method` distribution | `no_match`: 24 |
| `match_score` distribution | `0`: 24 |
| `verified` null | 24/24 |
| `ai_confidence` null | 24/24 (expected — `--no-ai`) |

**Output CSV columns:** `code, drug_name, matched_product_name_en, matched_product_name_ar, matched_store_product_id, match_score, verified, match_method, ai_confidence, ai_review_confidence`

**Sample row:** `79407, LILI FEMININE WASH 250ML, "", "", "", 0.0, NaN, no_match, NaN, NaN`

---

## Run 2: Augmented Catalog (148 rows, with exact synthetic matches)

| Metric | Value |
|---|---|
| Exit code | 0 |
| Elapsed | 1.69s |
| Total products | 24 |
| Matched | **0** |
| `match_method` distribution | `component_index`: 24 |
| `match_score` distribution | `100`: 24 |
| `verified` null | 24/24 |
| `ai_confidence` null | 24/24 (expected) |

**Sample row:** `79407, LILI FEMININE WASH 250ML, "", "", "", 100.0, NaN, component_index, NaN, NaN`

**ملاحظة مهمة:** الـ augmented catalog فيه exact match لـ"LILI FEMININE WASH 250ML" (row 101). الـ matcher المفروض يلاقيه بـ100%. بدل كده، بيرجع `score=100` لكن `matched_product_name_en` فاضي.

---

## Ad-hoc Verification Checks (6/8 PASS)

| # | Check | Result |
|---|---|---|
| 1 | Run 1 (real catalog) exit=0 | **PASS** ✅ |
| 2 | Run 2 (aug catalog) exit=0 | **PASS** ✅ |
| 3 | Run 1 elapsed < 30s (heuristic should be fast) | **PASS** ✅ (1.84s) |
| 4 | Run 2 elapsed < 30s | **PASS** ✅ (1.69s) |
| 5 | No RuntimeError in stderr | **PASS** ✅ |
| 6 | Real catalog has SOME heuristic hits (match_method != no_match) | **FAIL** ❌ |
| 7 | Aug catalog: at least 1 `matched_product_name_en` filled | **FAIL** ❌ |
| 8 | No critical errors in logs | **PASS** ✅ (0 warnings, 0 errors) |

**Result: 6/8 PASS** — الـ baseline `--no-ai` شغال من ناحية CLI plumbing، لكن فشل في الـ matching logic.

---

## الـ Bugs اللي طهرت

### 🐛 Bug #1 (Critical): `component_index` بيرجع score بدون product name

في الـ augmented run، كل المنتجات عندها `match_score=100` و `match_method=component_index`، لكن `matched_product_name_en` فاضي.

**التشخيص:** الـ `DrugIndex._brand_index` بيلاقي الـ matching components لكن مش بيختار أي Tawreed row. النتيجة: الـ matcher بيقول "أنا متأكدة 100%" لكن من غير evidence product.

**التأثير:** كأن الـ pipeline بتقول "كله matched" لما فعلاً مفيش ولا match واحد صالح.

### 🐛 Bug #2 (Medium): الـ brand index ما بيلاقيش brand tokens واضحة

في الـ real run، كل المنتجات `no_match` — يعني الـ brand index ما لقاش حتى component واحد صالح. ده محتمل لأن:
- الـ Tawreed catalog 100 rows قديم (2026-07-22)
- الـ brand tokens في الـ test products مش موجودة في الـ catalog (مثلاً "LILI", "GLIPTUS", "PEDIAMIL AR")
- الـ brand lookup محتاج refresh للـ catalog

### 🐛 Bug #3 (Low): Manual review queue logic معطوب

راجع تقرير الـ `--with-ai` report: المنتجات اللي `score=100` بتنزل في manual review بـ`reason_for_manual_review=no_match_found`. ده تناقض واضح — score=100 المفروض تتجاوز manual review.

---

## الـ Files المُنتجة

| File | Purpose |
|---|---|
| `no_ai_real.csv` | Real catalog run output |
| `no_ai_aug.csv` | Augmented catalog run output |
| `summary.json` | Structured summary (8 checks, 6 pass, 2 fail) |

الـ verify script (`hermes-verify-no-ai.py`) **اتحذف** من `%TEMP%` بعد الـ run.

---

## حدود الـ Verify

- مفيش `pytest` اتشغل — الـ memory بيقول إن الـ project test suite فيه pre-existing failures
- مفيش project lint اتشغل
- النتيجة adhoc على 24 sample فقط — مش representative
- الـ Tawreed catalog `100 products` صغير، فلو زادت عينات ممكن الـ brand index يلاقي matches

---

## Recommendation

**الـ `--no-ai` path مش جاهز للـ production** حتى بدون AI bugs اللي اكتشفناها قبل كده. الـ bugs في الـ heuristic matcher (component_index bug #1) بتخلي الـ pipeline:
- بتقول "score=100" لمنتجات مفيش لها match
- مش بتختار Tawreed product واحد
- بترمي كل المنتجات في manual review queue

**قبل ما تستخدم الـ CLI في production:**
1. أصلح `component_index` matcher (Bug #1) — لازم يرجع Tawreed row كامل
2. أصلح الـ manual review threshold logic (Bug #3)
3. حدّث الـ Tawreed catalog — الـ 100 rows قديمة ومش بتعكس الـ stock الحالي

**للـ quick sanity check:** شغّل الـ CLI بدون AI على 5-10 products موجودة في الـ catalog المحفوظ عندك، وتأكد إن `matched_product_name_en` فعلاً فيه اسم product مش فاضي.