# Phase 0.6 و0.7 — semantics وcandidate budget

## semantics موحّدة للحدود

أضيفت دالة مشتركة `normalize_candidate_limit` واستخدمتها مسارات:

- Excel-target save limit.
- Tawreed save limit.
- Excel-target review discovery limit.
- Streamlit display limit.
- استخراج خيارات manual review.

القواعد الآن موحّدة:

| الإدخال | القيمة الفعالة |
|---|---:|
| `0` أو قيمة سالبة | `1` |
| قيمة غير صالحة مثل `None` أو نص غير رقمي | default `5` |
| قيمة صحيحة موجبة | نفس القيمة |

## budget gate

أداة `report_excel_target_candidate_coverage.py` أصبحت تنتج `candidate_budget` لكل target، وتفحص:

- `candidate_count_generated.p99 <= 10`.
- `candidate_count_generated.max <= 25`.
- `candidate_count_saved.p99 <= 10`.
- `candidate_count_saved.max <= 25`.

يمكن تخصيص الحدود من CLI:

```powershell
& '.venv\Scripts\python.exe' tools/report_excel_target_candidate_coverage.py `
  --artifact-dir <artifact-dir> `
  --candidate-p99-limit 10 `
  --candidate-max-limit 25
```

الحالة تكون `pass` أو `fail`، وحالة `fail` تعيد exit code `2` حتى لا يمر threshold كتحذير صامت.

## الاختبارات

- مصفوفة semantics: `0`, السالب، `None`، النص غير الصالح، والقيم الصحيحة.
- report budget ينجح داخل الحدود ويفشل عند `p99/max` أقل من القيمة المقاسة.

آخر تحقق مركّز:

```text
11 passed
```
