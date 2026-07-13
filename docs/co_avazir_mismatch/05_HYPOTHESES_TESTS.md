# 5 — اختبارات الفرضيات (Hypothesis test files)

كل فرضية لها ملف اختبار تحت `tests/hypotheses/`.

## H1 — Brand containment / CO prefix  
`tests/hypotheses/test_h1_brand_containment_co_prefix.py`

- يثبت metrics: ratio∈[82,86), len_diff=2, containment
- يثبت أن `_brand_match_check` يجب أن يرفض الزوج (بعد الإصلاح)
- **Score: 95/100** — السبب الأساسي

## H2 — Missing storeProductId على المنتج الصحيح  
`tests/hypotheses/test_h2_correct_missing_store_product_id.py`

- بدون storeProductId → rejected + السبب يحتوي storeProductId
- مع storeProductId → accepted
- **Score: 78/100** — مساهم حاسم

## H3 — Safe omission + same form  
`tests/hypotheses/test_h3_safe_omission_and_form_ok.py`

- form الطرفين OINT
- لو نجح brand خطأ، سبب القبول يكون safe omission
- **Score: 55/100**

## H4 — Drops candidate (منفية)  
`tests/hypotheses/test_h4_drops_already_rejected.py`

- drops تُرفض (brand أو form)
- ليست best_match
- **Score: 10/100** — ليست السبب الحي

## H5 — Query generation (منفية)  
`tests/hypotheses/test_h5_query_generation_not_root.py`

- الاستعلامات تتضمن CO AVAZIR و OINT
- **Score: 5/100**

## اختبار إعادة الإنتاج الشامل  
`tests/test_co_avazir_mismatch.py`

| test | الغرض |
|------|-------|
| brand_check_rejects_avazir_for_co_avazir | H1 |
| wrong_candidate_alone_is_not_accepted | منع الاستبدال |
| correct_orderable_candidate_is_accepted | عدم كسر الصحيح |
| correct_beats_wrong_when_both_orderable | ترتيب صحيح |
| production_shape_wrong_not_chosen_over_unorderable_correct | مرآة الإنتاج |

### نتائج قبل الإصلاح
3 فشل / 5

### نتائج بعد الإصلاح
5 نجاح / 5
