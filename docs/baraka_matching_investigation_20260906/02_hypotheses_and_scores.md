# الفرضيات والدرجات

الدرجة هنا ثقة سببية من 10، وليست جودة دوائية. الاختبارات H1 وH2 حمراء عمدًا؛ والاختبارات الأخرى ضابطة كي لا نعالج مكوّنًا غير مسؤول عن المشكلة.

| الترتيب | الفرضية | اختبارها | النتيجة | الثقة | الحكم |
|---:|---|---|---|---:|---|
| H1 | بوابة القبول لا تطبق thresholds | `test_h1_production_matcher_must_honor_the_threshold_contract` | فشل: قبلت سالبوفنت | 10.0 | السبب الأساسي |
| H2 | `excelTarget` يعطل حارس identity | `test_h2_excel_target_requires_brand_identity_evidence` | فشل: rejection فارغ | 9.5 | سبب أساسي مشارك |
| H3 | الاسم العربي وضع في `productNameEn` | `test_h3_catalog_schema_is_single_name...` | نجاح: الحقلان متساويان وعربيان | 8.5 | سبب تمكيني |
| H4 | Cohere/cache/bilingual fallback هو من قبل الصف | `test_h4_bilingual_fallback_is_not_needed...` | نجاح: الخطأ يتكرر والـfallback معطل | 1.5 | مستبعد كسبب للـfalse positives |
| H5 | تشابه pack/form فقط يكفي | `test_h5_false_candidate_has_only_generic...` | نجاح: overlap 0.333 و`30` مشترك | 9.0 | آلية الاستغلال |
| H6 | saved manual review فرضت النتيجة | فحص final reason وreplay | لا يوجد `Approved by...` في المثال | 1.0 | مستبعد لهذا المثال |
| H7 | خطأ workbook/header/sheet | تحميل 4,107 صف والتحقق من headers | تحميل صحيح | 0.5 | مستبعد |
| H8 | query قصير هو السبب الوحيد | فحص query list وscore input | مساهم، لكن score يستخدم item الأصلي | 4.0 | عامل ثانوي |

## H1 — السبب الرئيسي

الكود الحالي يفصل بين rules المفترض وبين production الفعلي:

```text
matching_rules.acceptance_details(...)  -> يرفض candidate عند overlap=0.333
_diagnostic_acceptance(...)              -> يقبل candidate عند no extra numeric tokens
```

أي تعديل لـ`medium_score_threshold` أو`high_overlap_threshold` في YAML لن يحل الحالة ما دامت production لا تستدعي العقد. لذا تغيير threshold وحده ليس إصلاحًا.

## H2 وH3 — لماذا يظهر مع البركة

Tawreed عادة يملك اسمًا إنجليزيًا/هوية منفصلة، فيستطيع guard مقارنة token مثل `INODEP`. كتالوج البركة يملك اسمًا واحدًا عربيًا. `TargetProduct.to_candidate_dict()` ينسخه إلى `productNameEn` و`productName`، ثم `_candidate_variant_rejection()` يستثني كل `excelTarget` من `_missing_english_identity_reasons()`.

العربية ليست مشكلة بذاتها؛ المشكلة أن البرنامج لا يطلب أي إثبات bilingual للعلامة قبل auto-match. يجب أن يكون dictionary hit أو cached translation موثوق أو قرار يدوي محدد هو الدليل، وليس تشابه `30` أو `150 ML`.

## H4 — مشكلة تشغيلية مرتبطة

كانت توجد مسبقًا تعديلات غير ملتزمة في `excel_target_matching.py` و`bilingual_brand_matcher.py` تستهدف cache-only ورفع `bilingual_min_score` من 0.70 إلى 0.75. لم ألمسها. هي مهمة لاستهلاك Cohere وscore scale، لكن المثال الخطأ يحدث مع `enable_bilingual_secondary_match=False`؛ فلا تعتبر إصلاحًا للسبب الحالي.

## H8 — query variants

`JACKODAN FACIAL WASH 150ML` يولد `JACKODAN 150` في أول القائمة. في Excel in-memory تمر كل rows مع أول query ثم تزال التكرارات، بينما scoring نفسه يستعمل `item.name`. لا يفسر ذلك قبول INODEP، لكنه يجعل `best_match_query` مضللًا ويوسع سطح generic candidates. يعالج بعد H1/H2 لا قبله.

