# 4 — الأدلة من الملفات ونتائج التشغيل

## 4.1 وجود المنتج الصحيح في الكتالوج المحلي

تم البحث في:

```
data/input/tawreed_products.csv
```

وظهر السطر:

```csv
ريتشي بانثينول ادفانس كريم,U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM,2685228.0,,110.0
```

هذا يثبت أن المنتج الصحيح موجود في الكتالوج المحلي المتاح داخل المشروع. لا يثبت وحده أن نفس `storeProductId` كان orderable في نتيجة API الحية لذلك run.

## 4.2 نتيجة التشغيل في `order_result_summary_20260629_1429.csv`

السطر الخاص بالصنف `91167`:

```csv
91167,U RICHI PANTHENOL ADVANCE CREAM GEL 50M,7,0,not-orderable,No decisive match found for 'U RICHI PANTHENOL ADVANCE CREAM GEL 50M' after 11 queries.,U RICHI FACIAL WASH FOR NORMAL SKIN 50 ML,...
```

الدلالات:

1. الحالة النهائية `not-orderable`/no decisive match.
2. النظام جرب 11 query في هذا run.
3. أفضل اسم ظهر في summary هو `FACIAL WASH` وليس المنتج الصحيح.
4. وجود `FACIAL WASH` كأفضل مرشح يعني أن البحث لم يكن فارغاً، بل كان هناك ranking خاطئ/رفض خاطئ.

## 4.3 المنتج الصحيح/الأقرب ظهر في `matching_trace_20260629_1429.csv`

من trace:

```csv
matching,91167,U RICHI PANTHENOL ADVANCE CREAM GEL 50M,...,
9,U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM,...,
2442366,True,2.563272,False,,"Semantic token conflict: CREAM vs GEL, GEL vs CREAM",...
sequence_score=0.987654
overlap_score=0.9625
numeric_overlap=1.0
exact_bonus=2.0
availability_bonus=1.0
semantic_penalty=-20.0
```

هذا هو الدليل الحاسم: المرشح قريب جداً، orderable، وفيه الاسم الصحيح تقريباً، لكن تم رفضه بسبب rule semantic conflict.

ملاحظة: `store_product_id` هنا `2442366` وليس `2685228`. هذا يعني أن نتائج البحث المحفوظة في ذلك run احتوت إدراجاً orderable آخر بنفس/قريب من الاسم، بينما الكتالوج المحلي يحتوي أيضاً `2685228`. في كلتا الحالتين المشكلة الأساسية واحدة: الاسم الصحيح/القريب نفسه يُرفض بسبب CREAM/GEL.

## 4.4 مرشح آخر قريب جداً رُفض لنفس السبب

من trace:

```csv
U RICHI PANTHENOL CREAM GEL 50 GM,2670885,True,0.758562,False,
"Semantic token conflict: CREAM vs GEL, GEL vs CREAM"
```

هذا يثبت أن المشكلة ليست خاصة بكلمة `ADVANCE` فقط. أي منتج يحتوي `CREAM GEL` يمكن أن يتعرض لنفس الرفض.

## 4.5 سبب صعود المرشحات الخاطئة

في نفس trace، المرشح الأول:

```csv
U RICHI FACIAL WASH FOR NORMAL SKIN 50 ML,2569730,True,11.094136,False,
Semantic token conflict: different_modifier
```

رغم أنه خاطئ، score الخاص به أعلى من المنتج الصحيح لأن عقوبته أخف.

## 4.6 خيارات Manual Review محفوظة في JSONL

ملف:

```
artifacts/order/wardany/20260629_1429/manual_review_candidates_20260629_1429.jsonl
```

السطر الخاص بالصنف يحتوي الخيارات التي ذكرها المستخدم تقريباً:

```json
{
  "item_key": "91167::U RICHI PANTHENOL ADVANCE CREAM GEL 50M",
  "options": [
    {"name_en": "U RICHI FACIAL WASH FOR NORMAL SKIN 50 ML", "store_product_id": "2569730"},
    {"name_en": "U RICHI FACIAL WASH FOR OILY SKIN 50 ML", "store_product_id": "2342768"},
    {"name_en": "U RICHI U RICHI BODY OIL 50 ML", "store_product_id": ""},
    {"name_en": "CALCITONIUM 50 I.U. / ML 5 AMPS", "store_product_id": "2552982"},
    {"name_en": "U RICHI PANTHENOL CREAM 50 GM", "store_product_id": "2442364"}
  ]
}
```

الدلالة: صفحة Manual Review لا تبني هذه القائمة لحظياً؛ هي تقرأها من ملف الـ artifact.

## 4.7 نفس المشكلة تكررت عبر runs أحدث

البحث داخل artifacts أظهر نفس القائمة تقريباً في runs متعددة:

```
20260624_1055
20260627_1429
20260629_1429
20260701_1401
20260702_1104
20260704_1043
20260705_1413
20260706_1107
20260707_1228
20260707_1435
20260707_1456
20260708_1616
20260709_1139
20260709_1147
20260709_1201
```

هذا يثبت أنها ليست حادثة مؤقتة أو cache عابر، بل rule/systematic behavior.

## 4.8 الأدلة من الكود على أن `needs_correction` لا يفرض match

في `manual_review_runtime.py`:

```python
if not decision or not decision.approved:
    return None
```

أي decision غير approved لا ينتج forced match.

وفي `manual_review_helpers.py`:

```python
def _preferred_queries(decision):
    if decision.correct_query:
        return [decision.correct_query]
```

أي `needs_correction` يستخدم correct_query كبحث مفضل فقط.

## 4.9 الأدلة من الكود على أن Manual Review UI يقرأ JSONL فقط

في `streamlit_manual_review_page.py`:

```python
candidates_dict = load_review_candidates(run_dir)
```

وفي `manual_review_candidate_store.py`:

```python
file_path = run_dir / f"manual_review_candidates_{run_dir.name}.jsonl"
```

لا توجد إعادة بحث ولا call لـ Tawreed API عند فتح الصفحة.
