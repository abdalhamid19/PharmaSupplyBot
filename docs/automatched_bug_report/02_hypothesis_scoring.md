# 02 — اختبار الفرضيات والتقييم (Hypothesis Testing & Scoring)

> منهجية: لكل سبب محتمل ملف اختبار مستقل يُثبت/ينفي الفرضية إجرائياً. الدرجة = الاحتمال المسبق (prior) × التأكيد التجريبي. الأعلى درجة = السبب المرجّح.

---

## 1. منهجية التقييم

```
score = prior × confirmation
prior        : احتمال مسبق مبني على التحليل الساكن وتاريخ git (0-100)
confirmation : 1 إذا أكّدت الاختبارات الفرضية، 0 إذا رفضتها
```

**ملفات التنفيذ:**
- الإطار المشترك: `tests/hypotheses/automatched/_framework.py`
- العدّاء المجمّع: `tests/hypotheses/automatched/run_all.py`
- ملفات الفرضيات: `h1..h6`

**الأمر:**
```powershell
.venv\Scripts\python.exe tests\hypotheses\automatched\run_all.py
```

---

## 2. النتائج قبل الإصلاح (التشخيص)

```
=== SCORING SUMMARY (prior x confirmation) ===
  95  [H1] tuple truthiness always-true at call site      -> CONFIRMED  ★ السبب الجذري
  40  [H3] manual_review_required routes items away       -> CONFIRMED  (سلوك مشروع)
   0  [H2] enable_auto_save_verified_match disabled       -> rejected
   0  [H4] _preserve_existing_decision blocks upsert      -> rejected
   0  [H5] forced manual-review guard skips all saves     -> rejected
   0  [H6] DB write silently fails                        -> rejected

MOST LIKELY ROOT CAUSE: [H1] tuple truthiness always-true at call site
```

### 2.1 التفصيل قبل الإصلاح

| الملف | الاختبارات | نتيجة محددة أثبتت الفرضية |
|---|---|---|
| `h1_tuple_truthiness.py` | 3 (فشلان يؤكدان) | `assertFalse(skip)` → `AssertionError: True is not false` + `production flow saves nothing` → `store contains: []` |
| `h2_config_flag_off.py` | 3 ناجحة | الفلاغ الافتراضي `True`؛ الحفظ ينجح عندما نتجاوز الحارس يدوياً — الفلاغ ليس المشكلة |
| `h3_manual_review_required.py` | 3 (فشل واحد مقصود) | الأصناف ذات status قابل للمراجعة لا تصل للحفظ أصلاً — سلوك صحيح حسب التصميم |
| `h4_preserve_existing.py` | 3 ناجحة | `_preserve_existing_decision` يعمل فقط عند وجود قرار بشري سابق (`approved_match`/`not_matching`) |
| `h5_forced_match_guard.py` | 2 ناجحة | حارس 999 يتطلب شرطين معاً — لا يمنع التدفق العادي |
| `h6_db_write_failure.py` | 2 ناجحة | `ManualReviewStore.upsert` على قاعدة مؤقتة يكتب ويقرأ بنجاح |

---

## 3. تفصيل كل فرضية

### H1 — معاملة الـ tuple كـ boolean  ★ (prior 95, CONFIRMED)

**الادعاء:** `if should_skip_auto_save_verified_match(...):` يقيم `(False, "...")` كـ True فيخرج مبكراً في كل مرة.

**الأدلة التجريبية (قبل الإصلاح):**
1. `assertIsInstance(result, tuple)` ✓ العقد tuple.
2. `bool((False, "No conflicts detected")) == True` ✓ دائماً truthy.
3. مسار الإنتاج الكامل: تطابق مثالي + فلاغ مفعّل → **صفر صفوف**.
4. سجل git: الحارس دخل في `3d3191c` (2026-07-05) وآخر `auto_matched` حقيقي قبله.
5. DB الفعلي: كل `auto_matched` من `csv_import` (لا يمر بالحارس).

**لماذا prior=95؟** تفسير وحيد لكل الأدلة الخمسة معاً؛ لا توجد فرضية بديلة تشرح "الصمت التام" في كل التشغيلات.

### H1b — مُستخرج الشركة المصنّعة المعطوب (سبب مساعد داخل H1)

**الادعاء:** حتى بعد إصلاح الـ tuple، الفحص التقريبي للتضارب يمنع الحفظ لمعظم الأصناف.

**الدليل:**
```
'PANADOL EXTRA 24 TAB'  → item_mfg='EXTRA'  vs  candidate companyName='GSK'  → conflict=True ❌
```
الخوارزمية: "آخر token غير رقمي وغير موجود في `_GENERIC_IDENTITY_TOKENS`". القائمة تفتقد EXTRA, ULTRA, PANADOL, AVAZIR... أي أن **اسم المنتج نفسه** يُعتبر شركة. **النتيجة:** لو أُصلح H1 وحده (حل S1) لاستمر انسداد الحفظ بنسبة تقديرية 60-80% من الأصناف.

### H2 — فلاغ `enable_auto_save_verified_match` معطّل (prior 30, rejected)

**كيف اختُبرت:** قراءة الافتراضي من `MatchingConfig` + تشغيل المسار بمثلث حالات الفلاغ.
**النتيجة:** الافتراضي `True` في `MatchingConfig`؛ `config.yaml` لا يضبطه (يبقى بالافتراضي). **مرفوضة** — الفلاغ ليس السبب (لكن بقي اختبار حرس).

### H3 — `manual_review_required` يحوّل الأصناف بعيداً (prior 40, CONFIRMED كسلوك)

**الادعاء الأصلي:** الأصناف كلها تُوجّه لمراجعة بشرية فلا تصل للحفظ.
**النتيجة:** `manual_review_required` يعتمد على `status` فقط (`REVIEWABLE_STATUSES` مثل `no-results`); أصناف `matched` لا تدخل المراجعة. **سلوك صحيح حسب التصميم** — ليست خطأً، لكنها "مسار منافس" يستحق اختبار حرس.

### H4 — `_preserve_existing_decision` يمنع الـ upsert (prior 25, rejected)

**كيف اختُبرت:** قاعدة فارغة → الحارس لا يجد قراراً سابقاً → لا يمنع. الحارس يعمل فقط مع قرار بشري سابق (وهذا مقصود).
**النتيجة:** مرفوضة.

### H5 — حارس المطابقة القسرية 999 يمنع الكل (prior 15, rejected)

**كيف اختُبرت:** الشرط `score == 999.0 AND "Approved by saved manual review" in final_reason` — لا يتحقق للتطابقات العادية (95).
**النتيجة:** مرفوضة.

### H6 — فشل كتابة DB صامت (prior 5, rejected)

**كيف اختُبرت:** `upsert` ثم `list_decisions` على قاعدة مؤقتة → الصف موجود. `execute_update` يعمل commit صريحاً.
**النتيجة:** مرفوضة.

---

## 4. النتائج بعد الإصلاح (حرسات انحدار)

نفس الملفات حُوّلت إلى regression guards — أي "CONFIRMED" الآن يعني **انحداراً** (رجوع الخطأ):

```
=== SCORING SUMMARY (post-fix, regression guards) ===
  40  [H3] manual_review_required routing semantics   -> CONFIRMED (سلوك، ليس خطأ)
  30  [H2] enable_auto_save flag semantics            -> CONFIRMED (سلوك، ليس خطأ)
   0  [H1] tuple truthiness (regression guard)        -> rejected ✅ الخطأ لم يعد
   0  [H4] preserve-existing semantics                -> rejected
   0  [H5] forced-999 guard semantics                 -> rejected
   0  [H6] DB persistence                             -> rejected
```

**H1 (السبب الجذري) أصبح rejected = الإصلاح فعّال ومستمر.**

---

## 5. مصفوفة الأدلة الشاملة

| الدليل | يدعم H1 | يدعم H1b | يدعم غيرها |
|---|---|---|---|
| `bool((False, str)) == True` (بايثون) | ✅ حاسم | — | — |
| Reproduction: تطابق مثالي → 0 صفوف | ✅ حاسم | ➕ متسق | — |
| DB: كل auto_matched = csv_import | ✅ | — | — |
| توقيت 3d3191c = بداية الانقطاع | ✅ | ➕ (نفس commit فترة) | — |
| 'PANADOL EXTRA'→EXTRA conflict | — | ✅ حاسم | — |
| الافتراضي True للفلاغ | — | — | ❌ ينفي H2 |
| قاعدة فارغة تُحفظ بنجاح | — | — | ❌ ينفي H6 |

**الترجيح النهائي: H1 سبب جذري أساسي، H1b سبب مساعد كان سيمنع الحل الجزئي.**
