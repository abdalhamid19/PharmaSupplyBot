# حالة Gate 0 وGold Set في 2026-09-11

هذا الملف يسجل ما تم تنفيذه بعد replay المقارن، وما بقي قبل تغيير ترتيب
المرشحين أو توسيع الاستدعاء.

## ما تم تنفيذه

- أضيفت أداة قراءة فقط: `tools/excel_target_replay_manifest.py`.
- تسجل الأداة commit الكود، بصمة التغييرات المحلية، نسخة Python، بصمة ملفات
  الاعتمادات، config، ملف الطلب، workbooks الأهداف، prevented items، وقواعد
  البيانات.
- تحسب `target_catalog_fingerprint` من الصفوف المحملة canonicalized، وليس من
  وقت تعديل الملف.
- أضيفت اختبارات تمنع الكتابة على workbooks أو SQLite أثناء بناء manifest.
- تم توسيع `gold_labels.csv` ليشمل `expected_row_key` و`label`.
- أضيفت حالات موجبة للصف الصحيح في `VOLTAREN 3AMP` و`XITHRONE 500MG 3TAB`
  في الهدفين، مع حالات سالبة قريبة لـ6 أمبول و5 أقراص.
- أضيفت للمقياس labels من النوع `P` و`N_variant` و`N_prefix` و`U` و`E_stale`.
  لا تدخل `U` و`E_stale` في مقام precision.
- أضيفت `recall@1` و`recall@3` و`recall@5` للمرشحين المحفوظين.
- عدّل تنبيه Manual Review ليعرض `Review-only candidate; human approval
  required` لكل قنوات review-only، بما فيها `cross_language_alias`.

## نتيجة القياس على run 20260911_1436

النتائج التالية تخص الصفوف المعلّمة فقط، وليست تقديرًا نهائيًا لـprecision
على كل الكتالوج:

| الهدف | الحالات الموجبة المحفوظة | precision المعلّم | recall@1 | recall@3 | recall@5 |
|---|---:|---:|---:|---:|---:|
| البركة شركات | 2 | 50% | 0% | 100% | 100% |
| القيصر شركات | 2 | 50% | 100% | 100% | 100% |

الـ50% ناتجة عن عينة صغيرة فيها مرشحان موجبان ومرشحان سلبيان معلّمان لكل
هدف. لا يجوز استخدامها وحدها لتغيير threshold أو تفعيل automatic matching.

## ملاحظة عن الـmanifest

تم توليد manifest للـrun في:

`artifacts/order/wardany/20260911_1436/replay_manifest.json`

وهو manifest post-hoc للـartifacts الموجودة. قبل replay release جديد يجب توليد
manifest قبل التشغيل بنفس الملفات، ثم التحقق من ثبات hashes بين before وafter.

## القرار الحالي

لا نفعّل `cross_language_aliases_enabled` في config production بناءً على هذه
العينة وحدها. الاستدعاء الصحيح موجود بالفعل في `C_generated` و`C_saved` لهذه
الحالتين، لكن ترتيب `VOLTAREN 3AMP` في البركة يحتاج دراسة منفصلة بعد توسيع
العينة وتصنيف المرشحين الباقين.

## المتبقي بعد Phase 2 وقبل Phase 3

1. قياس `C_display` من boundary الحقيقي في Streamlit، لا استنتاجه من saved.
2. إضافة replay manifest قبل التشغيل إلى runbook والمقارنة.
3. توسيع labels البشرية المستقلة قبل إعلان precision gate.
4. تثبيت round-trip وfail-closed end-to-end.
5. دراسة ترتيب المرشح الصحيح في البركة بعد اتساع العينة، دون خفض thresholds
   قبل وجود labels كافية.
