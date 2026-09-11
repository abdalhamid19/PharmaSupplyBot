# Phase 0.2 — قياس `C_display` الفعلي

## النتيجة

تم تنفيذ harness مستقل read-only يستدعي مسار Streamlit الحقيقي:

```text
load_review_candidates
→ _load_group_candidates
→ _filter_and_prepare_items
→ _paginate_candidates
→ _limit_candidates_by_source
→ _render_item_card (capture boundary)
```

الـ harness لا يفتح SQLite الحقيقي، ولا يشغّل `run.py`، ولا يكتب إلى workbook أو artifacts. تم استبدال decision store ببديل read-only، وتم تسجيل الخيارات عند الحد الفاصل قبل بناء widgets.

## التغيير القابل للتدقيق

- سجلات JSONL الجديدة التي تكتبها `append_review_candidates` تحتوي الآن على `candidate_count_saved` صريح.
- القراءة الصارمة لا تستخدم `len(options)` كـ fallback.
- حقل مفقود ينتج `status=not_measured`.
- اختلاف `candidate_count_saved` عن عدد `options` ينتج `status=inconsistent`.
- القياس يلتقط `candidate_method` و`ranking_tier` و`excel_target_row_key` مع كل بطاقة.

## قياس run حقيقي

تم القياس على run `20260911_1609` المدموج من:

- `artifacts/excel-target/البركة شركات/20260911_1609`
- `artifacts/excel-target/القيصر شركات/20260911_1609`

الأمر المستخدم:

```powershell
& '.venv\Scripts\python.exe' tools/measure_excel_target_c_display.py `
  --run-dir 'artifacts/excel-target/البركة شركات/20260911_1609' `
  --run-dir 'artifacts/excel-target/القيصر شركات/20260911_1609' `
  --display-limit 5
```

النتيجة:

| المقياس | القيمة |
|---|---:|
| `C_saved_artifact` | 495 |
| `C_loaded_unique` | 495 |
| `C_display_run` | 418 |
| `C_display_pages` | 143, 163, 91, 21 |
| البطاقات المعروضة | 164 |
| invariants | PASS |

القيمة الأقل لـ`C_display_run` متوقعة لأن العرض الحالي يمر عبر حد `5` مرشحين لكل بطاقة، مع pagination ودمج المصدرين. لا تعني أن المرشحين فُقدوا من artifact؛ الفرق بين `495` و`418` هو فرق طبقة العرض فقط.

## الاختبارات

أضيفت اختبارات تغطي:

- القياس الصريح وعدم fallback.
- فشل القياس عند mismatch.
- حد عدد المرشحين مع الحفاظ على row keys.
- pagination لـ`51` بطاقة دون فقد أو تكرار.
- عدم إسقاط صفّي Excel لهما نفس product identity وrow keys مختلفة.
- استقلال `hide_completed` عن `C_saved_artifact`.

التحقق:

```text
46 passed
```

كما نجح `py_compile` للأداة والـwriter، ونجح تشغيل القياس على run الحقيقي. ظهرت فقط تحذيرات Streamlit المتوقعة لأنه تشغيل خارج runtime؛ لم ينتج عنها أي كتابة.

## حدود النتيجة

القياس الحالي يعرض targetين في union واحد، لذلك أرقام `C_*` أعلاه للـmerged run وليست تفصيلاً منفصلاً لكل target. فصل القياس لكل target ممكن بتشغيل الأداة مرة لكل run directory، وهو مطلوب قبل استخدام الأرقام كبوابة rollout مستقلة لكل مخزن.
