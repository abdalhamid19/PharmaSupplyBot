# التحقق من الفرضيات والحلول

## baseline

قبل إضافة alias Tawreed، كانت بوابة Excel-target الآمنة خضراء لكنها لا تحتوي اختباراً يثبت استخدام ملف Tawreed. أضيف اختبار أحمر أولاً:

```text
test_tawreed_catalog_alias_can_identify_target_row_without_live_translation
```

فشل الاختبار لأن `excel_target_identity` لم يكن يحتوي حتى على `load_tawreed_catalog`. هذا يثبت فجوة التكامل، لا مجرد مشكلة بيانات.

## scorecard الفرضيات (baseline قبل التحسينات الأخيرة)

| الفرضية | الدليل | الدرجة / 10 | الحكم |
|---|---|---:|---|
| Arabic-only بلا identity | 42 من 50 في artifact baseline تحمل سبب identity نفسه | 10.0 | سبب أساسي |
| Tawreed catalog غير موصول بمسار Excel-target | alias مفيد موجود، ولا import في المسار قبل الإصلاح | 9.5 | سبب أساسي ثان |
| translation cache غير مكتمل | المسار cache-only ولا يترجم أثناء run | 8.5 | سبب مهم |
| قاموس Egyptian غير كافٍ | 17 من 42 بلا hit في `lookup_en` | 8.5 | سبب مهم |
| compatibility صارم | 4 حالات identity/variant مرفوضة | 6.0 | سلوك أمان، ليس bug عام |
| خطأ تحميل workbook | catalog size كان 4107 | 1.0 | مستبعد للـrun المدروس |
| browser/API | Excel-target in-memory وmatch-only | 0.5 | مستبعد |

## اختبار الحل

الاختبارات الجديدة تغطي:

1. alias Tawreed يعرّف صفاً موجوداً في البركة دون translation live.
2. alias لا يقبل صفاً عربياً غير متعلق.
3. alias يحفظ كل variants، ولا يحذف variant قبل فحص التركيز.
4. dictionary matches الحالية لا تتراجع.
5. English exact match يبقى ناجحاً.
6. no-results يبقى للحالة التي لا يوجد فيها دليل هوية.

## نتائج التنفيذ

```text
87 passed, 8 subtests passed in 27.41s
```

تشمل:

- اختبارات Excel-target.
- اختبارات الأمان الخاصة بالبركة.
- اختبارات الفرضيات.
- scorecard.
- product matching.
- Excel-target E2E.

## نتيجة replay المصغر على Baraka (baseline تاريخي)

تم تحميل 4,107 صفاً من:

```text
data/input/excel target/البركة شركات.xlsx
```

النتائج:

- `PRIMOXIZAR 400MG`: match من `dictionary`.
- `BRAYTOFLEX 30 TAB`: match من `dictionary`.
- `INODEP CAPSULES 30`: no-results لأن صف Baraka العربي غير موجود.
- `OXILAGE 20TAB`: no-results لأن صف Baraka العربي غير موجود.
- `PANTOGAR 60 CAP`: no-results لأن صف Baraka العربي غير موجود.

وفي replay الأخير بعد إضافة تطبيع `MGC/FLIM`، aliases التغليف، وتقرير coverage:
`13 matched-only` و`37 no-results`. المطابقات الإضافية الآمنة شملت PANTOGAR،
AUGRAM، AVETRIX، AGGREX، ALPHINTERN، BIVATRACIN، وASMAKAST. من حالات
no-results توجد `29` حالة نقص دليل هوية و`8` حالات هوية/variant مرفوضة.
لذلك لا يصح تفسير نسبة 74% كدليل على أن 74% من الأدوية غير متوفرة؛ هي نسبة قرارات
رفض/مراجعة آمنة في هذه العينة.

هذا هو السلوك الآمن: ملف Tawreed لا يخلق availability في Baraka.

## ما لم يتم الادعاء به

لا يمكن إعلان أن نسبة `no-results` ستنخفض في run الحالي بدون إدخال أسماء عربية جديدة فعلياً في كتالوج البركة أو إضافة aliases/قرارات manual review صحيحة. الإصلاح يزيل فجوة كود، لكنه لا يخلق بيانات غير موجودة.
