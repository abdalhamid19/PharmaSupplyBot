# Phase 0.3 و0.4 — round-trip وfail-closed

## round-trip e2e

تم اختبار المسار الكامل:

```text
append_review_candidates
→ manual_review_candidates_*.jsonl
→ load_review_candidates
→ _load_group_candidates
```

الـfixture يحتوي على خيارين لهما نفس:

- `store_product_id`
- الاسم والمصدر والهدف

لكن لكل منهما `excel_target_row_key` مختلف (`row-a` و`row-b`). النتيجة: الخياران بقيا مستقلين، ولم تُفقد أي من الحقول التالية:

- `target_key`
- `source_file`
- `candidate_method`
- `ranking_tier`
- `score_margin`
- `identity_evidence_kind`
- `compatibility_status`
- `excel_target_row_key`

## fail-closed e2e

تم تمرير كل evidence kinds التالية عبر `ExcelTargetMatcher.match` الفعلي:

```text
review_identity
review_identity_prefix
review_fuzzy
english_fuzzy
arabic_fuzzy
cross_language_alias
cohere_translation
discovery_only
```

لكل حالة ثبت الاختبار:

- `decision.best_match is None`.
- المرشح يظهر في `review_candidates` فقط.
- لا يتم استدعاء `ManualReviewStore.upsert`.
- row الصحيح يبقى مربوطًا بالـcatalog row المحدد.

كما استمرت اختبارات trusted native/dictionary identity الموجودة في النجاح، لذلك الحاجز لا يعطل مسار المطابقة الموثوق.

## ملاحظة تصحيح الاختبار

المحاولة الأولى استخدمت patch على instance داخل `ExcelTargetBilingualIndex` و`ExcelTargetReviewDiscoveryIndex`. كلاهما frozen dataclass، فظهر `FrozenInstanceError`. تم تتبع السبب وإصلاح الاختبار إلى patch على class methods فقط؛ لم يتطلب الأمر أي تغيير في production matcher.

## التحقق

```text
test_full_match_fails_closed_for_every_review_only_evidence_kind: 8 passed
round-trip + candidate recall suite: 17 passed
```
