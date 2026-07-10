# 6 — الحلول الممكنة والمقايضات

## الحل 1: إصلاح `_semantic_conflicts` حتى لا يعتبر المجموعة المتطابقة تعارضاً

### الفكرة

إذا كانت مجموعة الـ form tokens في query تساوي مجموعة الـ form tokens في candidate، فلا يوجد conflict.

مثال:

```
query_forms     = {CREAM, GEL}
candidate_forms = {CREAM, GEL}
```

يجب أن يكون الناتج:

```
conflicts = ∅
```

بدلاً من:

```
{(CREAM, GEL), (GEL, CREAM)}
```

### التطبيق المحتمل

في `src/core/matching/matching_penalties.py` داخل `_semantic_conflicts`:

```python
for group in CONFLICT_GROUPS:
    query_group = query_tokens & group
    candidate_group = candidate_tokens & group
    if query_group == candidate_group:
        continue
    conflicts.update(...)
```

### المميزات

- أصغر تعديل ممكن.
- يحافظ على رفض الحالات الحقيقية مثل `CREAM` مقابل `LOTION` أو `SYRUP` مقابل `DROPS`.
- يحل مباشرة bug `CREAM GEL` عندما يظهر في الطرفين.

### المخاطر

- لو هناك منتجات تحتوي أكثر من form token فعلاً لكنها ليست صيغة مركبة، قد يقل rejection قليلاً. هذا خطر محدود لأن التساوي الكامل في tokens يعني الطرفين يحتويان نفس forms.

### الترجيح

مقترح أساسي وضروري.

## الحل 2: تعريف forms المركبة مثل `CREAM GEL` كـ token مركب واحد

### الفكرة

بدلاً من التعامل مع `CREAM` و`GEL` كتوكنين منفصلين، يمكن تحويل `CREAM GEL` إلى `CREAM_GEL` قبل semantic conflicts.

### المميزات

- أكثر صراحة في تمثيل الشكل المركب.
- يحل حالات مشابهة مثل `EMULGEL` أو `CREAM-GEL` لو أضيفت.

### العيوب

- تعديل أكبر في normalization.
- يحتاج تحديث أكثر من مكان وربما يؤثر على scoring والتطبيع.
- قد يتطلب توسيع ALIAS_TO_CANONICAL.

### الترجيح

حل جيد على المدى المتوسط، لكنه أكبر من المطلوب حالياً. الحل 1 أبسط وأكثر أماناً.

## الحل 3: تعديل Manual Review options لتضم candidates عالية التشابه قبل العقوبة

### الفكرة

بدلاً من `decision.diagnostics[:5]` فقط، نختار candidate options بطريقة مركبة:

1. أول 5 حسب score النهائي.
2. candidates ذات overlap/sequence عالي حتى لو rejected.
3. candidates التي تحتوي كل tokens الهوية الأساسية (brand + modifier + ingredient).
4. candidate الذي جاء من `correct_query` إن وجد.

### المميزات

- يمنع اختفاء المنتج الصحيح من واجهة Manual Review.
- يحسن تجربة المستخدم حتى عند وجود rule rejection.

### العيوب

- لا يحل فشل المطابقة التلقائي وحده.
- يحتاج test إضافي لترتيب candidates.
- قد يزيد خيارات review إذا لم يُضبط limit جيداً.

### الترجيح

حل مهم كتحسين UX بعد إصلاح السبب الأساسي.

## الحل 4: عند `needs_correction` إذا ظهر exact name من `correct_query`، يتم اعتباره forced match محدود

### الفكرة

حالياً `needs_correction` يضيف query فقط ولا يفرض match. يمكن إضافة منطق:

- إذا decision.manual_decision == `needs_correction`.
- والـ candidate name يساوي `correct_query` تقريباً بعد normalization.
- والـ candidate orderable.
- والـ numeric/form tokens متوافقة.

عندها يقبل candidate أو يضعه أعلى القائمة.

### المميزات

- يجعل تصحيحات المستخدم أقوى وأكثر احتراماً.
- يقلل الحاجة لإعادة مراجعة نفس الصنف.

### العيوب

- خطر أعلى: المستخدم قد يكتب query واسعاً وليس اسم منتج محدداً.
- يحتاج validation صارم حتى لا يتحول `correct_query` إلى bypass خطير.

### الترجيح

ليس الحل الأول. يمكن تطبيقه لاحقاً بعد وضع tests قوية.

## الحل 5: تحديث صفحة Manual Review لإعادة البحث عند وجود Saved Correction

### الفكرة

عند فتح item لديه `needs_correction`، تعرض الواجهة زر `Refresh candidates using saved correction` أو تعيد البحث تلقائياً.

### المميزات

- يعالج مباشرة شكوى "الاختيارات التي تظهر كلها خطأ".
- يجعل التصحيح اليدوي مرئياً في الواجهة دون انتظار run جديد.

### العيوب

- يحتاج API/client داخل UI أو تشغيل subprocess.
- قد يبطئ صفحة Streamlit.
- يحتاج إدارة credentials/session.

### الترجيح

مفيد لكن أكبر نطاقاً. لا يوصى به كأول تعديل جراحي.

## الحل 6: تحسين normalization لـ `50M` → `50 GM` عندما السياق يشير إلى grams

### الفكرة

لو token آخر يشير لـ topical product (`CREAM`, `GEL`, `OINTMENT`) والاسم ينتهي بـ `50M`، يمكن اعتبارها typo لـ `50 GM`.

### المميزات

- يحسن queries.
- يعالج أخطاء Excel الشائعة.

### العيوب

- قد يخطئ مع `50 ML` في منتجات سائلة/غسول.
- يحتاج قواعد سياقية دقيقة.

### الترجيح

ليس أول حل لأن المنتج ظهر بالفعل. يمكن إضافته لاحقاً إذا تكررت مشكلة `M`/`GM`.

## التوصية النهائية

ابدأ بـ:

1. إصلاح `_semantic_conflicts` لحالة المجموعات المتطابقة.
2. إضافة unit test يثبت أن `CREAM GEL` مقابل `CREAM GEL` لا ينتج conflict.
3. إضافة test كامل لـ `explain_best_product_match` للصنف `U RICHI PANTHENOL ADVANCE CREAM GEL 50M` مع candidate الصحيح.
4. بعدها قيّم الحاجة لتحسين Manual Review Top-N.
