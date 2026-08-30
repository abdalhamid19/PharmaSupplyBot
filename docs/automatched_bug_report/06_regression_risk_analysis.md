# 06 — تحليل مخاطر الانحدار والتوصيات (Regression Risk & Recommendations)

---

## 1. المخاطر المباشرة للإصلاح

| الخطر | الاحتمال | الأثر | التخفيف المُطبَّق |
|---|---|---|---|
| نمو قاعدة البيانات بسرعة (كل تطابق يُحفظ الآن) | مرتفع (متوقّع ومقصود) | حجم DB يزيد؛ upsert بمفتاح مركّب يمنع التكرار | المفتاح الأساسي `(item_code_key, item_name_key)` = صف واحد لكل صنف، ليس لكل تشغيل |
| حفظ تطابق خاطئ كـ `auto_matched` ثم اعتماده لاحقاً | متوسط | يعيد استخدام تطابق خاطئ في تشغيلات لاحقة | فلاغ `enable_auto_match_re_review_on_fail` يعيد المراجعة عند فشل؛ الحماية من الرفض الصريح باقية؛ المستخدم يمكنه تفعيل `enable_manufacturer_check` |
| فقد الحماية من تضارب الشركة المصنّعة افتراضياً | متوسط | لا يمنع الحفظ عند تضارب اسمي | مقصود: الفحص كان معطوباً ينتج رفضاً وهمياً؛ متاح بـ opt-in؛ محرك المطابقة نفسه (`matching_penalties`, `product_matching_acceptance`) لا يزال يرفض التضاربات الحقيقية قبل الوصول للحفظ |
| كسر قرارات بشرية سابقة | منخفض جداً | فقد عمل يدوي | `_preserve_existing_decision` مُختبَر (h4 + postfix test 4) |

## 2. مخاطر إصلاح مهلة الملاحة (resilient_goto)

| الخطر | التخفيف |
|---|---|
| retry يخفي مشكلة شبكة دائمة | retry **واحد فقط**؛ الفشل الثاني يرفع الاستثناء (مُختبَر: `test_persistent_timeout_still_raises`) |
| زيادة زمن الفشل في حالة انقطاع كامل | 60s × 2 = 120s كحد أقصى للملاحة الواحدة، مقابل انهيار التشغيل كاملاً سابقاً |
| retry على أخطاء غير المهلة (DNS مثلاً) | لا retry — يُرفع فوراً (مُختبَر: `test_non_timeout_error_propagates_without_retry`) |

## 3. توصيات مستقبلية (غير مُطبَّقة — تستحق تصميماً منفصلاً)

### 3.1 إصلاح بنيوي لـ `extract_manufacturer_from_name` (أولوية عالية)

المشكلة البنيوية: الخوارزمية الحالية "آخر token غير عام = الشركة المصنّعة" مبنية على افتراض خاطئ عن تسمية الأدوية.

خيارات التصميم:
1. **قاموس شركات موثوق** — جدول شركات مصنّعة من بيانات Tawreed نفسها؛ الاستخراج يصبح lookup لا تخميناً.
2. **حقل صريح فقط** — الاعتماد على `companyName`/`supplierName` من المرشح فقط، وعدم استنتاج شركة من اسم الصنف إطلاقاً (الأبسط والأدق).
3. **إشارة ثقة بدل قرار ثنائي** — إرجاع درجة ثقة تُدخل في الـ scoring بدل منع/سماح قاطع.

**التوصية:** الخيار 2 — إذا لم توفّر بيانات الصنف شركة صريحة، لا تخمّن. هذا يجعل `enable_manufacturer_check=True` مفيداً بحق.

### 3.2 عقد أنواع صريح لمنع تكرار خطأ الـ tuple

هذا الخطأ نوع من أخطاء "العقد الضمني". اقتراحات:
- **type checker في CI** (mypy/pyright): `if <tuple>:` في شرط منطقي يُلتقط كـ truthiness غير مقصودة مع الإعدادات المناسبة.
- **NamedTuple بدل tuple عادي**: `class SkipDecision(NamedTuple): skip: bool; reason: str` — الاستخدام يصبح `decision.skip`، والخطأ يصبح مستحيلاً نصياً.
- **اختبار عقد**: `assert isinstance(result, tuple) and len(result) == 2` في نقاط الحدود.

**التوصية:** NamedTuple — أرخص تغيير، يقتل صنف الخطأ بالكامل.

### 3.3 مقياس صحة لحفظ auto_matched (رصد تشغيلي)

الخطأ عاش ~8 أسابيع بلا كشف لأن **لا شيء يراقب أن الحفظ يعمل**. اقتراح:
- عدّاد في نهاية كل تشغيل match-only: `auto_saved_count`, `auto_save_skipped_count` مع أسباب التخطي المجمّعة.
- تنبيه إذا كان `auto_saved_count == 0` مع وجود تطابقات ناجحة.

الـ logging المُضاف (`_log_auto_save_skip`) خطوة أولى؛ العدّاد المجمّع هو الخطوة الثانية.

### 3.4 معالجة الإخفاقات الثمانية الموروثة

8 اختبارات فاشلة في baseline (فرع `logging_system`) — ليست من هذا العمل لكنها تخفي انحدارات مستقبلية. تستحق جلسة منفصلة:
- 3 في `test_cli_commands.py` (سلوك CLI/خروج)
- 2 في logging e2e
- 1 logging audit (`test_no_print_calls_in_src`)
- 1 matching logging async
- 1 cart removal

## 4. ما يجب مراقبته بعد النشر

```powershell
# 1) هل تُكتب صفوف auto_matched جديدة؟
.venv\Scripts\python.exe -c "import sqlite3;con=sqlite3.connect(r'state\manual_review_decisions.db');print(con.execute(\"SELECT run_id, COUNT(*) FROM manual_review_decisions WHERE manual_decision='auto_matched' GROUP BY run_id ORDER BY 2 DESC LIMIT 5\").fetchall())"

# 2) هل هناك تخطيات غير متوقعة؟ ابحث في اللوجز:
Select-String -Path logs\*.log -Pattern "auto-save skipped" | Select-Object -Last 20

# 3) هل ما زالت الملاحة تفشل بالمهلة؟
Select-String -Path logs\*.log -Pattern "navigation timed out" | Select-Object -Last 10
```

**علامات نجاح:** صفوف `auto_matched` بـ `run_id` جديد؛ رسائل "auto-save skipped" قليلة ومفهومة؛ رسائل "navigation timed out; retrying once" نادرة (وتتبعها متابعة ناجحة بدون انهيار).
