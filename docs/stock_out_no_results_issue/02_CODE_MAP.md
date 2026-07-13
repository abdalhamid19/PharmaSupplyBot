# 02 — خريطة الكود المتورط

## تدفق المعالجة (من الطلب إلى status)

```text
order item
  → require_product_match()                 [tawreed_search_logic.py]
      → saved_manual_review_decision()      [manual_review_runtime.py]
      → manual_review_queries()             prepend correct_query/name
      → search_products() per query
      → manual_review_result()              force approved name/id match
      → explain_best_product_match()        auto matcher
           → _diagnostic_acceptance()      [product_matching_acceptance.py]
                → _numeric_acceptance()     unrequested numeric tokens
                → _orderable_acceptance() / _unorderable_acceptance()
      → if no best_match:
           raise no_results_exception("No decisive match found...")
  → SummaryStatus.skip_status / failure_status
      → unmatched_decision_status()
           → _diagnostic_missing_orderable_identity()
  → order_item_summary row
```

## الملفات الحرجة

### 1) `src/core/matching/product_matching_acceptance.py`

- `_diagnostic_acceptance`: يقرر قبول/رفض كل مرشح.
- `_numeric_acceptance`: يرفض إذا كان في اسم المرشح أرقام غير موجودة في الاستعلام وغير “safe omission”.
- `_orderable_acceptance`: إذا القبول ناجح و`storeProductId` فارغ → `Candidate missing orderable storeProductId`.
- **`_unorderable_acceptance` (جديد):** إذا لا يوجد `storeProductId` والرفض soft numeric بدرجة ≥ 9 → يعيد صياغة السبب إلى missing storeProductId.

**سبب المشكلة هنا:** قبل الإصلاح، فشل numeric كان يُرجع مباشرة، فلا يصل مسار missing-id أبداً.

### 2) `src/tawreed/tawreed_summary.py` — `SummaryStatus`

```python
# unmatched_decision_status → not-orderable فقط إذا:
# 1) reason يحتوي "candidate missing orderable storeproductid"
# أو
# 2) score >= 12 وبدون hard rejection
```

قبل الإصلاح:

- reason = `unrequested numeric token: ...`
- score ≈ 10 < 12
- النتيجة: `""` → fallback **`no-results`**

### 3) `src/core/manual_review/manual_review_helpers.py`

`_find_name_match_in_candidates` كان يفعل:

```python
if not candidate_store_product_id(candidate):
    continue  # يتجاهل كل صف غير قابل للطلب
```

لذلك `approved_match` بالاسم فقط **لا يعمل** على HALOPERIDOL (spid فارغ دائماً) ولا على HAEMOJET عندما يظهر بدون spid.

### 4) `src/tawreed/matching/tawreed_search_logic.py`

- `require_product_match` / `_handle_no_match` يرفع `No decisive match found...`.
- `manual_review_result` بعد الإصلاح: إذا فرض تطابق اسم بلا spid → `skip_item_exception(... not orderable ...)`.

### 5) `src/core/ordering/order_run_artifact_rows.py`

عند status=`not-orderable` يملأ أسماء المنتج من diagnostics / blocked_candidate.  
عند `no-results` غالباً تبقى حقول المطابقة فارغة أو أقل فائدة.

## إعدادات ذات صلة

من `state/config.yaml` / `MatchingConfig`:

- `medium_score_threshold: 12.0` — عتبة كانت تُستخدم ضمنياً في not-orderable.
- لا يوجد إعداد منفصل لـ “soft numeric OOS recognition floor” (ثابت الكود: 9.0).

## لماذا LIMITLESS ينجح في نفس المسار؟

الاستعلام يحتوي نفس الأرقام تقريباً → `_numeric_acceptance` ينجح → `_orderable_acceptance` يرفض بـ missing storeProductId → score عالي → status=`not-orderable`.
