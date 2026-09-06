# إعادة الإنتاج والأدلة

## النطاق

الأمر محل التحقيق هو:

```powershell
C:\pc\py\pyreview\PharmaSupplyBot\.venv\Scripts\python.exe run.py order --config state\config.yaml --excel data\input\order_items\0000000000006777.xlsx --limit 50 --all-profiles --excel-target "البركة شركات" --excel-target-path "البركة شركات=data\input\excel target\البركة شركات.xlsx" --match-only --execution-mode api --item-workers 1 --prevented-items-excel data\input\prevented_items\drugprevented.xlsx --matching-risk-policy safe --flagged-match-action manual-review-only --stop-flag artifacts\run-control\order\order_stop.flag
```

`--match-only` يمنع الإضافة للسلة. مسار Excel target يبدأ قبل تشغيل profiles، ويقرأ workbook إلى الذاكرة ثم ينفذ `find_best_match_in_target`; لذلك يمكن اختبار سبب الخطأ بشكل حتمي بلا Tawreed API أو حساب مستخدم أو متصفح.

## فحص ملفي الإدخال

| الملف | Sheets | الصفوف | الأعمدة | الملاحظة |
|---|---:|---:|---|---|
| `data/input/order_items/0000000000006777.xlsx` | `Sheet1` | 1,260 | `الكود`، `إسم الصنف`، `الكمية المطلوبة` | مصدر طلب سليم |
| `data/input/excel target/البركة شركات.xlsx` | `2` | 4,107 | `شركات `، `سعر ج`، `الكود`، `الصنف` | كتالوج أسماء عربية فقط عمليًا |

إعدادات target تقرأ `الصنف` كاسم، و`الكود` كمعرّف. تم تحميل 4,107 صفوف بنجاح؛ لا يوجد دليل على خطأ header أو sheet أو column mapping.

## إعادة إنتاج حتمية مصغرة

استُخدم نفس دالة الإنتاج، مع عنصر حقيقي من order file ومرشح مطابق لصف حقيقي في كتالوج البركة:

```python
item = Item(code="90951", name="INODEP CAPSULES 30", qty=1)
catalog = [TargetProduct("unrelated-30", "سالبوفنت 30 قرص", 1.0, 0.0)]
decision = find_best_match_in_target(item, "baraka-diagnostic", catalog, config).decision
```

| المطلوب | ما تم قبوله | score | final reason |
|---|---|---:|---|
| `INODEP CAPSULES 30` | `سالبوفنت 30 قرص` | 12.3333 | `Accepted best candidate because No extra numeric tokens.` |

هذا reproduction حتمي وبلا شبكة. وهو الاختبار الأحمر `test_h1_production_matcher_must_honor_the_threshold_contract`.

## أدلة من التشغيل الحقيقي

في الفحص المباشر للكتالوج الحقيقي، أعادت دالة الإنتاج أمثلة غير صحيحة:

| item | candidate المقبول | score | overlap على الاسم الكامل |
|---|---|---:|---:|
| `JACKODAN FACIAL WASH 150ML` | `اليجا غسول للوجه 150 مل` | 11.00 | 0.20 |
| `INODEP CAPSULES 30` | `سالبوفنت 30قرص` | 12.33 | 0.333 |
| `SANSO B12 1000MGC` | `بى سويفت 1000مجم بديل دلتافيت` | 9.24 | 0.20 |

كلها قُبلت بالسبب نفسه: `No extra numeric tokens`. هذه الدرجات أدنى من حدود config (`medium_score_threshold=12`, `medium_overlap_threshold=0.6`, `high_overlap_threshold=0.85`) أو تخالف overlap المطلوب.

الأثر المتاح في `artifacts/order/wardany/20260905_1738/order_item_summary_20260905_1738.csv` يسجل Tawreed API: 46 `matched-only` و4 `not-orderable` من 50. هذا لا يثبت صحة كل 46 دوائيًا، لكنه يثبت فرق السلوك الملحوظ بين المصدرين.

## مسار البيانات وموضع الكسر

```text
Excel «البركة شركات»
  -> excel_target_loader._row_to_product
  -> TargetProduct.to_candidate_dict
       productNameEn = productName = الاسم العربي
  -> find_best_match_in_target
  -> explain_best_product_match
  -> _diagnostic_acceptance                 <-- بوابة القبول الخاطئة
  -> MatchDecision(best_match=...)          <-- يكتب matched-only
```

يوجد في `src/core/matching/matching_rules.py` عقد قبول كامل باسم `acceptance_details`: exact / high overlap / score + overlap / numeric + score. الاختبار الضابط يؤكد أنه يرفض مثال سالبوفنت (`overlap=0.333`). لكن `_diagnostic_acceptance` في `src/core/matching/product_matching_acceptance.py` لا يستدعيه؛ يستدعي `_numeric_acceptance` فقط، وذاك يرجع `True, "No extra numeric tokens"` عندما لا توجد أرقام زائدة.

## المتصفح وmatch trace

لم يُشغّل browser automation أو screenshot في إعادة الإنتاج، لأنهما لا يمران في مسار Excel target: الكتالوج in-memory و`--match-only` لا يفتح صفحة منتج للـExcel. استعمالهما هنا لن يضيف دليلًا سببيًا وسيخلط API/browser بالمشكلة المحلية. استُخدم فحص workbook وpytest وتشغيل دالة الإنتاج؛ وهي أدوات أدق للمسار المتضرر.

تمت قراءة `artifacts/match_traces/wardany_50.jsonl`: فيه 666 صفًا لاستعلام واحد (`ALFATHROMB 5 MCG 20 TABS`) وكلها `no brand match`. إنه trace للـbilingual tier ولا يسجل diagnostics لمسار canonical الذي قبل الأمثلة الخاطئة؛ لذلك لا يصلح وحده لإثبات بوابة القبول أو نفيها.

