# 03 — مقارنة الحلول واختبارها (Solution Comparison & Scoring)

> ملف الاختبار: `tests/solutions/test_solution_comparison_automatched.py` — يطبّق كل حل كنسخة محاكية لمسار الإنتاج ويقيسه بمعايير مرجّحة.

---

## 1. الحلول المرشحة

### S1 — الحد الأدنى (فك الـ tuple فقط)
```python
skip, _reason = should_skip_auto_save_verified_match(item, match.data, ...)
if skip:
    return
```
- ✅ يصلح "الموت الكامل" للحفظ
- ❌ يبقي مُستخرج الشركة المصنّعة المعطوب → 'PANADOL EXTRA' vs 'GSK' = تضارب وهمي → **معظم الأصناف لن تُحفظ بعد ذلك أيضاً** (انسداد جزئي 60-80%)

### S2 — فك الـ tuple + تقييد الفحص التقريبي بفلاغ (المُطبَّق) ★
```python
skip, skip_reason = should_skip_auto_save_verified_match(
    item, match.data, rejection_reason,          # السبب الحقيقي من diagnostics
    enable_manufacturer_check=bool(              # فلاغ موجود أصلاً في MatchingConfig
        matching_config and matching_config.enable_manufacturer_check
    ),
)
if skip:
    _log_auto_save_skip(item, skip_reason)       # لا صمت بعد الآن
    return
```
- ✅ يصلح الموت الكامل
- ✅ يلغي الرفض الوهمي (الفحص التقريبي opt-in)
- ✅ يحافظ على الحمايات: سبب الرفض الصريح من diagnostics + الفحص عند تفعيل المستخدم له
- ✅ logging يكشف أي تخطي مستقبلي

### S3 — حذف الحارس بالكامل (revert)
```python
# حذف استدعاء should_skip_auto_save_verified_match نهائياً
```
- ✅ يعيد سلوك ما قبل 3d3191c
- ❌ يفقد حماية "سبب الرفض الصريح" التي أُضيفت عمداً في 3d3191c

---

## 2. معايير التقييم والأوزان

| المعيار | الوزن | السؤال |
|---|---|---|
| `saves_auto_matched` | 3 | هل يُحفظ التطابق السليم كـ auto_matched؟ |
| `no_false_rejections` | 3 | هل الأسماء التجارية/كلمات الجرعة لا تُرفض وهمياً؟ |
| `conflict_protected` | 2 | هل يُمنع الحفظ عند رفض تضارب صريح؟ |
| `human_decision_preserved` | 2 | هل قرار البشر approved_match لا يُكدس فوقه؟ |
| `reviewable_status_safe` | 2 | هل الأصناف المحتاجة لمراجعة لا تُحفظ تلقائياً؟ |

## 3. مصفوفة النتائج (من الاختبارات الفعلية)

| المعيار (وزنه) | S1 الحد الأدنى | S2 المُطبَّق ★ | S3 الحذف |
|---|---|---|---|
| saves_auto_matched (3) | ⚠️ جزئي — فقط أصناف بلا companyName | ✅ كامل (3/3) | ✅ كامل (3/3) |
| no_false_rejections (3) | ❌ 0/3 عينات تنجح | ✅ 3/3 | ✅ 3/3 |
| conflict_protected (2) | ✅ | ✅ | ❌ (يفقد الحماية) |
| human_decision_preserved (2) | ✅ | ✅ | ✅ |
| reviewable_status_safe (2) | ✅ | ✅ | ✅ |
| **المجموع المرجّح (/36)** | **18** | **36** | **30** |

### تفصيل الأرقام
- S1: saves=1.5/3 (جزئي), false_rej=0/3, conflict=2/2, human=2/2, reviewable=2/2 → ~14-18
- S2: 3+3+2+2+2 = **36/36**
- S3: 3+3+0+2+2 = **30/36**

## 4. نتائج تشغيل الاختبارات

```
tests/solutions/test_solution_comparison_automatched.py
  S1MinimalTests::test_s1_scores                       PASSED  (يُثبت قصور S1)
  S2GatedTests::test_s2_conflict_protected             PASSED
  S2GatedTests::test_s2_human_decision_preserved       PASSED
  S2GatedTests::test_s2_no_false_rejections            PASSED
  S2GatedTests::test_s2_saves_healthy_match            PASSED
  S3NoGuardTests::test_s3_conflict_NOT_protected       PASSED  (يُثبت عيب S3)
  S3NoGuardTests::test_s3_human_decision_preserved     PASSED
  S3NoGuardTests::test_s3_saves_healthy_match          PASSED
========================= 8 passed =========================
```

## 5. القرار

**S2 هو الحل الأمثل** — الدرجة الكاملة 36/36:
1. يفتح الحفظ التلقائي بالكامل للأصناف السليمة.
2. يحافظ على كل الحمايات ذات المعنى (رفض تضارب صريح من محرك المطابقة، قرارات البشر، أصناف المراجعة).
3. يجعل الفحص التقريبي المعطوب **قابلاً للاختيار** بدل إجباره على الجميع.
4. يضيف رؤية (logging) لكل تخطٍ مستقبلي — لا مزيد من فشل الحفظ الصامت.

---

## 6. لماذا لم نُصلح `extract_manufacturer_from_name` في نفس الدفعة؟

| الخيار | القرار وقت اختيار S2 |
|---|---|
| توسيع `_GENERIC_IDENTITY_TOKENS` | مرفوض — عاجز بنيوياً: قائمة لا نهائية (كل اسم منتج/مادة فعالة/واصف جرعة ممكن) |
| استخدام LLM/قاعدة شركات خارجية | مرفوض — تغيير سلوكي كبير خارج نطاق إصلاح عاجل + يحتاج بيانات شركات موثوقة |
| opt-in flag (المُختار في S2) | إعادة السلوك للافتراضي الآمن فوراً، مع إبقاء الفحص متاحاً لمن يريده |

**تحديث:** الإصلاح البنيوي **نُفِّذ لاحقاً** في نفس الجلسة (الخيار 2 من التقرير 06): تعرُّف على قائمة `KNOWN_MANUFACTURERS` المُنسَّقة في جانب الصنف، و`companyName`/`supplierName` الصريح فقط في جانب المرشح. التفاصيل والقياسات: **[08_manufacturer_identity_fix.md](08_manufacturer_identity_fix.md)**.

الآن `enable_manufacturer_check=True` أصبح مفيداً بحق: يرفض `ORCHIDIA` مقابل `ORA` (تضارب حقيقي) ولا يرفض `EXTRA` مقابل `GSK` (تضارب وهمي).
