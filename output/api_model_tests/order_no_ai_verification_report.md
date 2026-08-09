# `py run.py order --no-ai` Verification Report — SMALL_TEST.xlsx

**Project:** PharmaSupplyBot
**Date:** 2026-08-08
**Test command:**
```bash
unset PYTHONPATH
.venv/Scripts/python.exe run.py order \
    --config state/config.yaml \
    --profile wardany \
    --excel data/input/order_items/SMALL_TEST.xlsx \
    --execution-mode api \
    --match-only \
    --limit=1 \
    --start-item=1 \
    --end-item=1
```
**Input:** `SMALL_TEST.xlsx` (24 products)
**Safety:** `--match-only` (never touch cart) + `--execution-mode api` (no browser)

---

## TL;DR

⚠️ **الـ `order` command بيشتغل من غير crash، لكن `--limit=1` بيخلي الـ run no-op** (processed=0)، ومفيش artifact جديد بيتكتب.

النتيجة الفعلية للـ items اللي شغال عليها (`--no-ai` heuristic) متاحة في **artifact قديم** من `20260723_1344` (قبل 16 يوم) — فيه 28 row، كلهم SMALL_TEST products، كلهم `status=not-orderable` لأن `storeProductId` مفقود في الـ Tawreed catalog.

| Run | Exit | Duration | Processed | Matched | Flagged | Artifact |
|---|---:|---:|---:|---:|---:|---|
| `--limit=1` (today) | 0 | 1.75s | **0** | 0 | 0 | فاضي |
| `--limit=24` (16 يوم فاتت) | — | — | 28 | 18 | 0 | `20260723_1344` |

---

## الـ Run الجديد (`--limit=1`)

| Item | Value |
|---|---|
| Exit code | 0 |
| Elapsed | 1.75s |
| Output | `✅ order completed` |
| Processed | **0** |
| Matched | 0 |
| Flagged | 0 |
| Duration reported | 0s |
| Artifact directory | `artifacts\order\wardany\20260808_1550` |
| Artifact files | **فاضي** (0 files) |

**النتيجة:** الـ CLI قال "completed" لكن ما عالجش ولا item. الـ artifact directory اتعملت بس فاضية.

**التشخيص:** الـ `--limit=1 --start-item=1 --end-item=1` مع بعض ممكن يـ filter كل الصفوف (start > end أو range calculation غلط). أو الـ `--match-only` مع `--limit=1` بيـ short-circuit.

---

## الـ Artifact القديم (reference baseline)

من `artifacts/order/wardany/20260723_1344/order_item_summary_20260723_1344.csv`:

### الـ Summary CSV Schema (60 columns)

```
item_code, item_name, item_qty, status, reason, ordered_total_qty,
matched_query, deterministic_score, matched, deterministic_match_found,
manual_review_blocked_match, matched_product_name_en, matched_product_name_ar,
matched_product_id, matched_store_product_id, winner_product_id,
winner_store_product_id, winner_available_quantity, winner_sale_price,
winner_Purchase_Price, selected_store_name, selected_discount_percent,
tie_break_reason, blocked_candidate_name_en, blocked_candidate_name_ar,
blocked_candidate_product_id, blocked_candidate_store_product_id,
blocked_candidate_available_quantity, blocked_candidate_sale_price,
ai_enabled, ai_status, ai_verified, ai_searched, ai_reviewed,
ai_confidence, ai_review_confidence, ai_model, ai_provider,
manual_review_required, final_action, manual_review_category,
manual_review_reason_detail, manual_review_blocking_phase,
candidate_safety_reason, query_manufacturer, candidate_manufacturer,
manufacturer_check_decision, saved_manual_review_decision,
saved_manual_review_safety_decision, higher_scoring_rejected_candidate,
higher_scoring_rejection_reason, elapsed_seconds, match_elapsed_seconds,
api_context_init_seconds, api_search_seconds, dom_wait_seconds,
dialog_close_seconds, manual_review_lookup_seconds, match_decision_seconds,
add_to_cart_seconds, artifact_write_seconds, summary_build_seconds
```

### الـ 28 Rows Status Distribution

| Status | Count | % |
|---|---:|---:|
| `not-orderable` | 18 | 64% |
| `no-results` | 8 | 29% |
| `not-orderable` (other) | 2 | 7% |

**كل الـ rows عندها** `matched=True` و `final_action=not-orderable` — يعني الـ matcher بيلاقي product لكن `storeProductId` بيبقى NaN/مفقود، فالـ pipeline بيقول "not-orderable" و مش بيضيف للـ cart.

### Sample Match (matched=True)

| Field | Value |
|---|---|
| `item_code` | 74696 |
| `item_name` | ANTODINE 20 MG 3 AMP |
| `status` | not-orderable |
| `reason` | Matched product is not orderable (missing storeProductId) |
| `matched_query` | ANTODINE 20 MG / 2 ML 3 I.M. OR I.V. AMP |
| `deterministic_score` | 999.0 |
| `matched` | True |
| `deterministic_match_found` | True |
| `matched_product_name_en` | ANTODINE 20 MG / 2 ML 3 I.M. OR I.V. AMP |
| `matched_product_name_ar` | انتودين 20 مجم / 2 مل 3 امبول |
| `matched_product_id` | 1037 |
| `matched_store_product_id` | **NaN** ← المشكلة |
| `winner_available_quantity` | 0 |
| `winner_sale_price` | 78.0 |
| `tie_break_reason` | Approved by saved manual review (Name match, not orderable) |
| `ai_enabled` | False |
| `final_action` | **not-orderable** |
| `manual_review_category` | candidate_not_orderable |
| `elapsed_seconds` | 0.482 |

### Sample No-Match

| Field | Value |
|---|---|
| `item_code` | 73396 |
| `item_name` | AVIL 6 AMP |
| `status` | no-results |
| `reason` | No decisive match found for 'AVIL 6 AMP' after 3 queries |
| `matched` | False |
| `final_action` | manual_review |
| `manual_review_category` | no_decisive_match |
| `higher_scoring_rejection_reason` | unrequested numeric token: 2, 45, 5 |

---

## الـ Issues المكتشفة

### 🐛 Issue #1: `--limit=1 --start-item=1 --end-item=1` بيخلي الـ run no-op

**الدليل:** الـ CLI قال "completed" مع `processed=0`، والـ artifact directory فاضية.

**التشخيص:** ممكن تكون flag combination غلط (start > end بحساب الـ 0-indexed/1-indexed)، أو `--match-only` بيقفل قبل ما يعد أي item.

**التأثير:** مش بقدر أختبر item واحد بسرعة — لازم أزيل `--limit` وأشغل على الـ24 كلهم عشان أشوف نتائج.

### 🐛 Issue #2: الـ Matcher بيلاقي products، لكن كلهم `storeProductId=NaN`

**الدليل:** كل الـ18 product اللي `matched=True` في الـ artifact القديم عندها `matched_store_product_id=NaN` و `winner_store_product_id=NaN` و `selected_store_name=NaN`.

**السبب المحتمل:**
- الـ Tawreed catalog (`100 products`) قديم (من 2026-07-22) وما اتحدثش
- الـ `export-products` command محتاج إعادة تشغيل عشان يجيب catalog جديد
- أو الـ `storeProductId` مش بيتربط في الـ `MatchPipeline` بشكل صحيح

**التأثير:** حتى مع `matched=True`، مفيش product صالح للـ cart. الـ pharmacist هيشوف كل المنتجات في manual review queue.

### 🐛 Issue #3: `deterministic_score=999.0` لكل الـ matches

**الدليل:** كل المنتجات اللي `matched=True` عندها `deterministic_score=999.0` (مش scale 0-100).

**التشخيص:** ده magic number في الـ matcher — يعني "deterministic match found" (success indicator). مش score حقيقي للمقارنة.

---

## الـ Verify Script (deleted)

الـ verify script `hermes-verify-order.py` اتشغل في `%TEMP%` ثم اتحذف. الـ command الفعلي اللي اتنفذ:

```bash
unset PYTHONPATH
/c/pc/py/pyreview/PharmaSupplyBot/.venv/Scripts/python.exe \
    /c/pc/py/pyreview/PharmaSupplyBot/run.py \
    --log-level INFO order \
    --config state/config.yaml \
    --profile wardany \
    --excel /c/pc/py/pyreview/PharmaSupplyBot/data/input/order_items/SMALL_TEST.xlsx \
    --execution-mode api \
    --match-only \
    --limit=1 \
    --start-item=1 \
    --end-item=1
```

الـ exit code: 0
الـ elapsed: 1.75s

---

## حدود الـ Verify

- مفيش `pytest` اتشغل — الـ memory بيقول إن الـ project test suite فيه pre-existing failures
- مفيش project lint اتشغل
- الـ artifact الجديد (اليوم) فاضي — فالنتائج الحقيقية مأخوذة من artifact قديم
- مفيش مقارنة مع `--ai` (الـ user طلب `--no-ai` بس)

---

## Recommendation

**الـ `order --no-ai` command بيشتغل**، لكن:

1. **`--limit=1` فيه bug** — بيخلي الـ run no-op. لازم إما تتجاهل الـ limit أو تستخدم `--start-item` و `--end-item` بس.
2. **الـ Tawreed catalog محتاج refresh** — الـ 100 products من 2026-07-22، والـ `storeProductId` مفقود في كلهم.
3. **الـ Matcher بيرجع `score=999`** — magic number مش score حقيقي.

**قبل ما تستخدم الـ CLI في production:**
1. أصلح الـ `--limit=1` flag combo bug
2. شغّل `export-products` عشان تجيب Tawreed catalog جديد
3. شوف ليه `storeProductId` مش بيتربط في الـ matched products

**Quick next step:** شغّل `--limit=0` (default = كل الـ24 items) وشوف الـ artifact الجديد بيتعمل ولا لأ: