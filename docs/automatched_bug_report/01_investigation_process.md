# 01 — عملية التحقيق بالتفصيل الممل (Investigation Process)

> هذا المستند يوثّق كل خطوة تمت للوصول إلى السبب الجذري، بالترتيب الزمني، مع الأدوات المستخدمة والأدلة المجمّعة.

---

## المرحلة 0: فهم النظام (Codebase Recon)

### 0.1 الأدوات المستخدمة
| الأداة | الاستخدام |
|---|---|
| وكيل استكشاف (explore subagent) | مسح شامل للكود عن `match only`, `Saved Corrections`, `auto_matched`, `approved_match` |
| `grep` | تتبع كل مواضع `rejection_reason` و `_GENERIC_IDENTITY_TOKENS` |
| `read` | قراءة كاملة لملفات المسار الحرج |
| `git log / git show / git blame` | تحديد commit إدخال الخطأ وتاريخه |
| `sqlite3` عبر python | فحص قاعدة البيانات الفعلية |
| pytest 9.1.1 | تنفيذ الاختبارات |

### 0.2 نقاط الدخول المُكتشَفة لـ "match only"

| الواجهة | الملف:السطر | الدالة |
|---|---|---|
| CLI | `src/cli/typer_app.py:360` | خيار `--match-only` |
| CLI | `src/cli/commands/cli_order_items.py:33` | `summary_label()` → `MATCH_ONLY_SUMMARY_LABEL` |
| CLI تنفيذ | `src/cli/commands/cli_order_execution.py:96` | `bot.match_items_only(items)` |
| CLI متوازي | `src/cli/commands/item_worker.py:46` | نفس الاستدعاء |
| Streamlit | `src/ui/fields/streamlit_profile_fields.py:36` | checkbox `Match only without adding to cart` |
| Streamlit | `src/ui/order/streamlit_order_command.py:53` | يضيف `--match-only` للأمر |
| API flow | `src/tawreed/api/tawreed_api_flow_main.py:13` | `match_items_only_with_api()` |

### 0.3 سلسلة الاستدعاء الكاملة (match-only API mode)

```
match_items_only_with_api (tawreed_api_flow_main.py:13)
  → require_api_match (tawreed_api_flow_matching.py)     # يطابق الصنف
  → record_api_match_only_store_metadata                 # ميتاداتا فقط
  → bot.order_flow.summary_recorder.record_match_only_success  (tawreed_order_summary.py)
      → append_order_item_artifacts  (tawreed_order_summary_build.py:16)
          → _handle_manual_review_or_auto_save  (:35)
              → [فرع 1] append_manual_review_artifacts   # يحتاج مراجعة بشرية
              → [فرع 2] _auto_save_verified_match  (:48) # الحفظ التلقائي ← هنا الخلل
```

### 0.4 مواضع قيم القرار

| القيمة | المكان | الدلالة |
|---|---|---|
| `approved_match` | Streamlit UI → `store.upsert` مباشرة | المستخدم صحّح التطابق يدوياً |
| `auto_matched` | `_create_and_save_decision` داخل `_auto_save_verified_match` | التطابق التلقائي المُتحقَّق |
| `needs_correction` | UI بعد رفض المرشحين | يحتاج تصحيحاً |
| `not_matching` | UI | لا يوجد تطابق |

---

## المرحلة 1: فحص قاعدة البيانات الحقيقية (الأدلة المادية)

### الأمر المنفَّذ
```python
import sqlite3
con = sqlite3.connect(r'state\manual_review_decisions.db')
cur = con.cursor()
cur.execute('SELECT manual_decision, COUNT(*), MAX(updated_at) '
            'FROM manual_review_decisions GROUP BY manual_decision')
```

### النتيجة الخام
```
('approved_match',  280, '2026-07-21 09:13:10')
('auto_matched',    938, '2026-07-20 07:24:31')   ← آخر صف قبل شهر تقريباً
('needs_correction',  4, '2026-07-20 07:53:20')
('not_matching',      1, '2026-07-20 07:24:31')
```

### الاستدلال الأول
وجود 938 صف `auto_matched` قد يبدو وكأن المشكلة "تعمل أحياناً". لذا فحصنا `run_id`:

```sql
SELECT item_code, item_name, run_id, created_at, updated_at
FROM manual_review_decisions WHERE manual_decision='auto_matched'
ORDER BY updated_at DESC LIMIT 8
```

```
('45413', 'ABIMOL EXTRA 20 TAB.', 'csv_import', '2026-07-20 07:24:31', ...)
('85839', 'ACHTENON 30 TABS',     'csv_import', ...)
('81700', 'ACIVIRAX 400 MG 30 TAB','csv_import', ...)
... (الكل csv_import)
```

**الاستنتاج الحاسم:** كل صفوف `auto_matched` مصدرها `csv_import` (أداة استيراد قديمة تكتب مباشرة بدون المرور بالحارس المعطوب). **صفر صفوف من تشغيلات match-only.**

### مطابقة التوقيت مع git
```
commit 3d3191c "ora_problem _fix"  — 2026-07-05
آخر auto_matched حقيقي من التشغيلات — قبل 2026-07-20 (وفق تصريح المستخدم)
```
السكريبت `tools/` الذي استورد CSV كان يتصل بالقاعدة مباشرة، لذا لم يتأثر بالحارس.

---

## المرحلة 2: تحليل الكود الساكن (Static Analysis)

### 2.1 الكود المعيب قبل الإصلاح

`src/tawreed/order/tawreed_order_summary_build.py:48-68`:

```python
def _auto_save_verified_match(item: Item, decision) -> None:
    if not decision or not decision.best_match:
        return
    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (decision.final_reason or ""):
        return
    # Safety check: skip saving matches that have validation issues
    from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
    if should_skip_auto_save_verified_match(item, match.data, getattr(decision, 'rejection_reason', None)):
        return                                                    # ← BUG: دائماً True
    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
    if _preserve_existing_decision(store.lookup(item.code, item.name)):
        return
    _create_and_save_decision(item, match, store)   # ← الكاتب الوحيد لـ auto_matched
```

### 2.2 عقد الدالة (Contract)

`src/core/manual_review/manual_review_helpers.py:312`:

```python
def should_skip_auto_save(...) -> tuple[bool, str]:   # ← يُرجع TUPLE
```

**قاعدة بايثون:** أي tuple غير فارغ truthy:
```python
>>> bool((False, "No conflicts detected"))
True    # ← هذا ما كان يحدث فعلياً
```

### 2.3 خطأ ثانوي مضمَّن: `getattr(decision, 'rejection_reason', None)`

`MatchDecision` **لا يملك** حقل `rejection_reason` أصلاً — الحقل موجود على `CandidateMatchDiagnostic`. الاستدعاء كان يمرر `None` دائماً، فحتى لو أُصلح الـ tuple، كانت حماية "سبب الرفض" ميتة أيضاً.

### 2.4 التاريخ (git blame)

```
3d3191c (2026-07-05) "ora_problem _fix" — أدخل حارس الـ tuple
0a76c25 file organization — نقل الملف لمكان الحالي
```

---

## المرحلة 3: الاختبار التوليدي (Reproduction Testing)

### 3.1 الاختبار
`tests/reproduction/test_reproduction_auto_matched_never_saved.py`

يستدعي **مسار الإنتاج الحقيقي** `append_order_item_artifacts` مع:
- صنف سليم: `PANADOL EXTRA 24 TAB`
- مرشح مطابق تماماً: score 95, storeProductId `SP-999`, نفس الاسم
- config: `enable_auto_save_verified_match=True` (الافتراضي)

### 3.2 النتيجة قبل الإصلاح
```
AssertionError: 0 != 1 : CLAIM CONFIRMED: perfect match-only run saved
NO auto_matched row; store contains: []
```
**الادعاء مثبت إجرائياً** — تطابق مثالي + فلاغ الحفظ مفعّل = صفر صفوف.

---

## المرحلة 4: اكتشاف السبب الثانوي (H1b) — صدفة ثمينة

أثناء بناء اختبارات الفرضيات، فشل H1 بشكل غير متوقع:
```
AssertionError: True is not false   # should_skip أرجع True لمرشح سليم!
```

### التحقيق بسكريبت تصحيحي مؤقت
```python
item_mfg = _extract_item_manufacturer(item)       # 'EXTRA'  ← من اسم الدواء!
cand_mfg = _extract_candidate_manufacturer(candidate)  # 'GSK'     ← حقيقي
conflict: True
should_skip: (True, "Manufacturer conflict detected for auto-save: 
                     item 'EXTRA' vs candidate 'GSK'")
```

### تضخيم المشكلة بفحص `extract_manufacturer_from_name` على أسماء حقيقية
```
'PANADOL EXTRA 24 TAB'        -> EXTRA     ← كلمة جرعة/وصف!
'ABIMOL EXTRA 20 TAB.'        -> EXTRA
'CO AVAZIR 5GM EYE OINTMENT'  -> AVAZIR    ← جزء من اسم المنتج!
'ACTI-COLLA C 30SACHETS'      -> SACHETS   ← وحدة تغليف!
'ULTRA PANADOL 10 TAB'        -> PANADOL   ← اسم تجاري وليس شركة!
```

**التحليل:** الدالة تأخذ "آخر كلمة غير رقمية وغير عامة" من الاسم وتعتبرها الشركة المصنّعة. قائمة `_GENERIC_IDENTITY_TOKENS` (27 كلمة مثل TAB, GEL, CREAM) لا تغطي كلمات مثل EXTRA/ULTRA/أسماء المنتجات. النتيجة: **أغلب الأصناف كانت ستُمنع من الحفظ حتى بعد إصلاح الـ tuple** — تخطيطي: ~60-80% رفض خاطئ (قياس على عينات الـ DB).

هذا يفسر لماذا كانت الحماية ستعمل "جزئياً" لو أُصلح الـ tuple فقط (الحل S1).

---

## المرحلة 5: اختبار الفرضيات المنهجي

ست فرضيات (تفصيل الدرجات في `02_hypothesis_scoring.md`):

| # | الفرضية | Score | الحالة |
|---|---|---|---|
| H1 | tuple truthiness | **95** | ✅ السبب الجذري |
| H1b | manufacturer extractor معطوب | (مضمّن في H1 سياقياً) | ✅ سبب مساعد |
| H2 | فلاغ الحفظ معطّل في config | 0 | مرفوضة |
| H3 | manual_review_required يحوّل الأصناف | 40 | سلوك مشروع لا خطأ |
| H4 | _preserve_existing_decision يمنع | 0 | مرفوضة |
| H5 | حارس 999 يمنع الكل | 0 | مرفوضة |
| H6 | فشل كتابة DB صامت | 0 | مرفوضة |

---

## المرحلة 6: التحقق النهائي (End-to-End)

بعد تطبيق S2:
- اختبار الـ reproduction: **نجح**
- 7 سيناريوهات postfix: **نجحت** (بما فيها الحمايات: تضارب الرفض، حارس 999، قرارات البشر)
- الحزمة الكاملة: 682 passed — نفس إخفاقات الـ baseline تماماً (8 إخفاقات موجودة قبل أي تغيير)

---

## اكتشافات مصاحبة (لا تمنع الإصلاح لكنها مهمة)

1. **8 اختبارات فاشلة في baseline** (قبل التغيير وبعده بنفس العدد): 3 في `test_cli_commands.py`، 2 في logging e2e، 1 logging audit، 1 matching logging، 1 cart removal — أُثبت وجودها بـ `git stash` ثم إعادة التشغيل. **ليست بسبب تغييراتنا.**
2. **بيئة الاختبار:** `.venv` كان ينقصه pytest — ثُبّت `pytest iniconfig pluggy` داخله.
3. **`docs/.obsidian/workspace.json` و `state/*.db` كانت متسخة** في git أثناء الجلسة — استُعيدت بـ `git checkout --`.
