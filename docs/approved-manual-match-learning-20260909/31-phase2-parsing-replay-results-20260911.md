# نتيجة Phase 2: parsing للرموز الملتصقة

## التغيير

تم توسيع `product_attributes.py` بحيث يتعرف مسار compatibility على:

- `3AMP` و`3 AMP` كـ ampoule مع pack يساوي 3.
- `3مبول` كـ ampoule مع pack يساوي 3.
- `3قرص` كـ tablet مع pack يساوي 3.
- alias العربية المختصرة `مبول`.

تمت إضافة negative cases صريحة لـ6 أمبول، و5 أقراص، وsyrup مقابل tablet.
الأدلة الناتجة تظل review-only؛ التعرف على attributes لا يضيف نوع evidence إلى
قائمة automatic identities.

## الاختبارات

- اختبارات parsing: `48 passed`.
- اختبارات candidate recall/identity/discovery/safety: `54 passed, 2 subtests`.
- replay الكامل بعد التغيير: run `20260911_1559`، وعدد العناصر `799` لكل target.

## مقارنة replay قبل وبعد

المقارنة بين `20260911_1436` قبل parsing و`20260911_1559` بعد parsing:

| الهدف | semantic rows المتغيرة | matched قبل | matched بعد | manual review قبل | manual review بعد |
|---|---:|---:|---:|---:|---:|
| البركة شركات | 0 | 154 | 154 | 105 | 105 |
| القيصر شركات | 0 | 109 | 109 | 149 | 149 |

لم يتغير automatic matched set أو عدد حالات manual review.

## أثر الصفين محل البلاغ

في الهدفين، الصف الصحيح لـ`VOLTAREN 3AMP` أصبح `compatibility_status=compatible`
بدل `candidate pack/form is not proven`، لكنه بقي خارج automatic matching لأن
الهوية العربية review-only. هذا هو السلوك الآمن المطلوب.

صف `XITHRONE 500MG 3TAB` بقي manual review لأن الصف العربي الصحيح لا يذكر القوة
`500MG` صراحةً؛ لذلك يسجل النظام `candidate strength is not proven` ولا يخترع
قوة غير موجودة في الكتالوج.

الصفّان الصحيحان ظلا داخل المرشحين المحفوظين، ونتيجة gold sample بقيت:

| الهدف | precision المعلّم | recall@1 | recall@3 | recall@5 |
|---|---:|---:|---:|---:|
| البركة شركات | 50% | 0% | 100% | 100% |
| القيصر شركات | 50% | 100% | 100% | 100% |

العينة صغيرة ومتعمدة، لذلك لا تكفي لتغيير ترتيب tiers أو تفعيل قناة جديدة.
الخطوة التالية المنفصلة هي دراسة ranking في البركة، ثم توسيع labels البشرية قبل
أي تعديل thresholds.
