# 3 — تحليل الأسباب الجذرية وترجيح السبب الأساسي

## الخلاصة التنفيذية

المشكلة ليست أن Tawreed لا يحتوي على المنتج الصحيح، وليست أن البحث لم يرجع أي نتائج. المنتج الصحيح/شبه الصحيح ظهر فعلاً في `matching_trace_20260629_1429.csv`، لكن خوارزمية الرفض الدلالي اعتبرت وجود كلمتي `CREAM` و`GEL` معاً تعارضاً قاتلاً.

السبب الأساسي المرجّح بدرجة عالية:

```
قاعدة CONFLICT_GROUPS تعتبر CREAM و GEL متعارضين دائماً،
حتى عندما يكون اسم الصنف واسم المرشح يحتويان على الاثنين معاً بصيغة مركبة مشروعة: CREAM GEL.
```

هذا أدى إلى:

1. المنتج الأقرب جداً `U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM` حصل على similarity عالية جداً، لكنه أخذ semantic penalty قاتل.
2. منتجات خاطئة مثل `FACIAL WASH` ظهرت في أعلى خيارات Manual Review لأن الـ top 5 مبني على score بعد العقوبة، وليس على مطابقة هوية المنتج فقط.
3. الـ saved correction كـ `needs_correction` لا يغيّر عرض الخيارات القديمة لأن صفحة Manual Review تعرض JSONL مكتوب مسبقاً، ولا تعيد البحث مباشرة بعد إدخال التصحيح.

## السبب الأساسي رقم 1: تعارض دلالي خاطئ بين CREAM و GEL

### أين موجود؟

في `src/core/matching_types.py`:

```python
CONFLICT_GROUPS = (
    frozenset({"ANISE", "CHAMOMILE", "CINNAMON", "CLOVE", "DETOX", "MINT"}),
    frozenset({"APPLE", "BANANA", "CHOCOLATE", "LEMON", "ORANGE", "STRAWBERRY"}),
    frozenset({"CREAM", "GEL", "LOTION", "OINTMENT", "SHAMPOO", "SOAP"}),
    frozenset({"DROPS", "INJECTION", "SYRUP", "VIAL"}),
)
```

وفي `src/core/matching/matching_penalties.py`:

```python
def _semantic_conflicts(query_tokens: set[str], candidate_tokens: set[str]) -> set[tuple[str, str]]:
    conflicts: set[tuple[str, str]] = set()
    for group in CONFLICT_GROUPS:
        query_group = query_tokens & group
        candidate_group = candidate_tokens & group
        conflicts.update(
            (left, right) for left in query_group for right in candidate_group
        )
    return {(left, right) for left, right in conflicts if left != right}
```

### ما الخطأ المنطقي؟

لو الـ query يحتوي `CREAM` و`GEL` معاً، والـ candidate يحتوي `CREAM` و`GEL` معاً أيضاً، فإن الكود ينتج:

```
(CREAM, GEL)
(GEL, CREAM)
```

ثم يحذف فقط الأزواج المتساوية مثل `(CREAM, CREAM)` و`(GEL, GEL)`، لكنه لا يفهم أن المجموعة الموجودة في الطرفين متطابقة.

بالتالي بدل أن يقول:

```
query forms    = {CREAM, GEL}
candidate forms= {CREAM, GEL}
لا يوجد تعارض، لأن الشكل المركب متطابق.
```

يقول:

```
Semantic token conflict: CREAM vs GEL, GEL vs CREAM
```

### لماذا هذا هو السبب الأساسي؟

لأن الـ trace يثبت أن المنتج الصحيح تقريباً ظهر:

```
U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
row_index=9
score=2.563272
rejection_reason="Semantic token conflict: CREAM vs GEL, GEL vs CREAM"
sequence_score=0.987654
overlap_score=0.9625
numeric_overlap=1.0
exact_bonus=2.0
availability_bonus=1.0
semantic_penalty=-20.0
```

أي أن كل مؤشرات التشابه ممتازة تقريباً، والعقوبة الوحيدة الكبيرة هي التعارض الدلالي المزدوج.

### لماذا منتجات Facial Wash صعدت فوق المنتج الصحيح؟

منتج خاطئ مثل:

```
U RICHI FACIAL WASH FOR NORMAL SKIN 50 ML
```

حصل على score أعلى (`11.094136`) رغم أنه مختلف تماماً، لأن عقوبته الدلالية أقل (`-4.0`) مقارنة بعقوبة المنتج الصحيح (`-20.0`).

هذا يفسّر لماذا الخيارات المعروضة كلها خاطئة: قائمة Manual Review تأخذ أول 5 diagnostics بعد ترتيب score، وليس أول 5 أقرب منطقياً بعد تجاهل bug التعارض.

## السبب رقم 2: `50M` في Excel ليست `50 GM`

اسم الصنف في Excel:

```
U RICHI PANTHENOL ADVANCE CREAM GEL 50M
```

والمنتج الصحيح:

```
U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM
```

هنا توجد مشكلة normalization محتملة: `50M` قد تُفهم كـ `50 M` وليس `50 GM`. هذا يؤثر على queries، حيث ظهرت queries مثل:

```
U RICHI PANTHENOL ADVANCE CREAM GEL 50M
U RICHI PANTHENOL ADVANCE CREAM GEL 50 M
U RICHI PANTHENOL ADVANCE
...
```

لكن هذا ليس السبب الأساسي، لأن المرشح الصحيح ظهر بالفعل في النتائج، وحصل على `numeric_overlap=1.0`. إذن المشكلة لم تكن في الوصول للمنتج، بل في رفضه بعد الوصول إليه.

الترجيح: سبب مساعد، وليس السبب الجذري.

## السبب رقم 3: Saved Correction من نوع `needs_correction` لا يعني "approved match"

الحالة التي ذكرها المستخدم:

```
manual_decision = needs_correction
approved        = FALSE
correct_query   = U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM (بحسب وصف المستخدم؛ لم أتحقق من قاعدة CockroachDB مباشرة)
```

منطق الكود يفرّق بين نوعين:

1. `approved_match`: يفرض مطابقة إذا ظهر `correct_store_product_id` أو `correct_product_name`.
2. `needs_correction`: يضيف `correct_query` كأول query، لكنه لا يفرض قبول النتيجة.

في `manual_review_runtime.py`:

```python
def manual_review_queries(...):
    preferred = _preferred_queries(decision)
    final_queries = [p for p in preferred if p]
    ...
```

وفي `manual_review_match()`:

```python
if not decision or not decision.approved:
    return None
```

بما أن `needs_correction` غالباً `approved=False`، فهي لا تتجاوز خوارزمية الرفض. هي فقط تجعل البحث يبدأ بالاسم الصحيح. لو خوارزمية الرفض نفسها بها bug، سيظل المنتج الصحيح يُرفض.

الترجيح: سبب مهم جداً في فهم لماذا التصحيح لم يحسم المطابقة، لكنه ليس bug مستقل؛ هو سلوك مصمم بهذا الشكل.

## السبب رقم 4: صفحة Manual Review تعرض candidates قديمة من JSONL ولا تعيد البحث

الخيارات الخاطئة في Manual Review تأتي من:

```
artifacts/order/wardany/20260629_1429/manual_review_candidates_20260629_1429.jsonl
```

الكود:

```python
def load_review_candidates(run_dir: Path) -> dict[str, list[ReviewCandidateOption]]:
    file_path = run_dir / f"manual_review_candidates_{run_dir.name}.jsonl"
    ...
```

هذه البيانات تُكتب مرة واحدة أثناء التشغيل عبر:

```python
options = review_candidate_options(decision, limit=5)
append_review_candidates(run.directory, item.code, item.name, options)
```

و`review_candidate_options()` يأخذ:

```python
decision.diagnostics[:limit]
```

أي أن صفحة Manual Review لا تعيد بناء خيارات الـ run القديم بعد التصحيح إلا إذا تم تشغيل مسار جديد ينتج JSONL جديداً، أو تمت إضافة آلية refresh صريحة. لذلك حتى لو أضفت correct_query في Saved Corrections، لن تتغير الخيارات القديمة تلقائياً.

الترجيح: سبب مباشر لعرض الخيارات الخاطئة في الواجهة، لكنه نتيجة ثانوية للسبب الأساسي.

## السبب رقم 5: Top-N candidates مبنية على score بعد العقوبات ولا تحتفظ بأقرب candidates مرفوضة لأسباب قابلة للإصلاح

المنتج الصحيح ظهر في matching trace لكنه لم يظهر في Top 5 لأن ترتيب diagnostics جعله في المرتبة 9 بسبب العقوبة `-20`.

هذا تصميم غير مثالي للـ Manual Review؛ لأن هدف الواجهة أن تساعد الإنسان، وبالتالي يجب ألا تخفي مرشحاً عالي التشابه بسبب rule rejection. الأفضل أن تضمّن:

1. أعلى score بعد العقوبات.
2. أعلى raw similarity قبل العقوبات.
3. أي candidate يطابق correct_query أو item name بدرجة عالية.
4. أي candidate اسمه يحتوي كل identity tokens الأساسية مثل `U RICHI + PANTHENOL + ADVANCE`.

الترجيح: سبب قوي في العرض فقط، وليس في فشل المطابقة الأساسي.

## ترتيب الأسباب حسب الترجيح

| الترتيب | السبب | الترجيح | لماذا |
|--------|-------|---------|------|
| 1 | تعارض `CREAM`/`GEL` الخاطئ داخل `CONFLICT_GROUPS` | مرتفع جداً | trace يثبت أن المنتج الصحيح رُفض بهذا السبب رغم similarity عالية. |
| 2 | `needs_correction` لا يفرض قبول match | مرتفع | correct_query يساعد البحث فقط ولا يتجاوز bug الرفض. |
| 3 | Manual Review تعرض JSONL قديم ولا تعيد البحث | مرتفع | يفسر بقاء الخيارات الخاطئة بعد حفظ التصحيح. |
| 4 | Top 5 مبنية على score بعد العقوبة | متوسط/مرتفع | يخفي candidate الصحيح من خيارات الإنسان. |
| 5 | `50M` بدل `50 GM` | متوسط/منخفض | قد يقلل جودة query، لكنه لم يمنع ظهور المنتج في results. |
