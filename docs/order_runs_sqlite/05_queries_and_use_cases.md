# 05 — الاستعلامات وحالات الاستخدام

الغرض من هذا الملف: إثبات أن المخطط يجيب فعلاً على الأسئلة المطلوبة. إن
احتاج سؤال ما إلى استعلام معقد أو مسح كامل للجدول، فذلك خلل في المخطط لا
في السؤال.

## 1. سؤالك الأصلي: كل المخازن لصنف في run معيّن

```sql
SELECT s.store_name,
       ris.available_qty,
       ris.public_price,
       ris.purchase_price,
       ris.discount_percent,
       ris.is_winner,
       ris.ordered_qty
FROM run_item_stores ris
JOIN stores s ON s.store_key = ris.store_key
JOIN items  i ON i.item_key  = ris.item_key
WHERE ris.run_key = 'wardany/20260830_1809'
  AND i.item_code = '12345'
ORDER BY ris.discount_percent DESC;
```

يستخدم الفهرس الأساسي `(run_key, item_key, store_product_id)` مباشرة.

## 2. أعلى مخزن خصماً لكل صنف في run

```sql
SELECT * FROM v_best_discount_per_item
WHERE run_key = 'wardany/20260830_1809';
```

بفضل عمود `rank_by_discount` المحسوب مسبقاً هذا مجرد فحص فهرس.

بدون العمود سيكون الاستعلام `ROW_NUMBER() OVER (PARTITION BY item_key
ORDER BY discount_percent DESC)` على كل الصفوف — أبطأ بكثير ويتكرر في كل
استعلام.

## 3. هل اختارت الاستراتيجية فعلاً أفضل مخزن؟

هذا سؤال **تحقُّق من صحة المنطق**، وهو أهم ما تفتحه القاعدة:

```sql
SELECT i.item_code, i.item_name,
       w.store_name  AS chosen_store,
       w.discount_percent AS chosen_discount,
       b.store_name  AS best_store,
       b.discount_percent AS best_discount,
       ROUND(b.discount_percent - w.discount_percent, 2) AS lost_pct
FROM (SELECT ris.*, s.store_name FROM run_item_stores ris
      JOIN stores s ON s.store_key = ris.store_key
      WHERE ris.is_winner = 1) w
JOIN (SELECT ris.*, s.store_name FROM run_item_stores ris
      JOIN stores s ON s.store_key = ris.store_key
      WHERE ris.rank_by_discount = 1) b
  ON b.run_key = w.run_key AND b.item_key = w.item_key
JOIN items i ON i.item_key = w.item_key
WHERE w.run_key = 'wardany/20260830_1809'
  AND b.discount_percent > w.discount_percent + 0.01
ORDER BY lost_pct DESC;
```

هذا يكشف كل حالة اختارت فيها `first_available` مخزناً أدنى خصماً من
المتاح. مستحيل الإجابة عن هذا اليوم لأن بيانات المخازن غير المختارة غير
محفوظة. عملياً: يقيس تكلفة استخدام `--warehouse-mode first_available`
مقابل `max_discount` بالأرقام، على بيانات حقيقية، بلا إعادة تشغيل.

## 4. تتبع سعر صنف عبر الزمن

```sql
SELECT r.run_id, r.started_at,
       s.store_name,
       ris.purchase_price,
       ris.discount_percent,
       ris.available_qty
FROM run_item_stores ris
JOIN runs   r ON r.run_key  = ris.run_key
JOIN items  i ON i.item_key = ris.item_key
JOIN stores s ON s.store_key = ris.store_key
WHERE i.item_code = '12345'
  AND ris.is_winner = 1
ORDER BY r.started_at;
```

هذا هو الاستعلام الذي يبرّر المشروع كله. اليوم يستلزم فتح كل مجلد run
وقراءة CSV وتصفية صف واحد.

## 5. أرخص مخزن لصنف تاريخياً

```sql
SELECT s.store_name,
       COUNT(*)                          AS appearances,
       ROUND(AVG(ris.discount_percent),2) AS avg_discount,
       MAX(ris.discount_percent)          AS best_discount,
       ROUND(AVG(ris.purchase_price),2)   AS avg_price
FROM run_item_stores ris
JOIN items  i ON i.item_key  = ris.item_key
JOIN stores s ON s.store_key = ris.store_key
WHERE i.item_code = '12345'
GROUP BY s.store_key
ORDER BY avg_discount DESC;
```

مخرَج مباشر: قائمة مرتبة تُستخدم لضبط `preferred_warehouses` في
`state/config.yaml` **بناء على بيانات** بدلاً من التقدير. الإعداد الحالي
يحتوي سبعة مخازن مرتبة يدوياً (`config.yaml:40-47`).

## 6. المخازن الأكثر موثوقية

```sql
SELECT s.store_name,
       COUNT(DISTINCT ris.item_key)                      AS items_offered,
       SUM(CASE WHEN ris.available_qty > 0 THEN 1 ELSE 0 END) AS in_stock,
       ROUND(100.0 * SUM(CASE WHEN ris.available_qty > 0 THEN 1 ELSE 0 END)
                   / COUNT(*), 1)                        AS stock_rate,
       ROUND(AVG(ris.discount_percent), 2)               AS avg_discount
FROM run_item_stores ris
JOIN stores s ON s.store_key = ris.store_key
JOIN runs   r ON r.run_key   = ris.run_key
WHERE r.started_at >= date('now', '-90 days')
GROUP BY s.store_key
HAVING items_offered >= 20
ORDER BY stock_rate DESC, avg_discount DESC;
```

يميّز بين «مخزن بخصم عالٍ لكنه دائماً نافد» و«مخزن بخصم متوسط لكنه متوفر
دائماً» — تمييز لا يستطيع `warehouse_strategy` الحالي إدراكه لأنه يرى
run واحداً.

## 7. أصناف تفقد التوفّر

```sql
WITH recent AS (
    SELECT ris.item_key,
           r.run_id,
           SUM(ris.available_qty) AS total_available,
           COUNT(*)               AS store_count
    FROM run_item_stores ris
    JOIN runs r ON r.run_key = ris.run_key
    WHERE r.started_at >= date('now', '-30 days')
    GROUP BY ris.item_key, r.run_key
)
SELECT i.item_code, i.item_name,
       MIN(store_count) AS min_stores,
       MAX(store_count) AS max_stores,
       AVG(total_available) AS avg_available
FROM recent
JOIN items i ON i.item_key = recent.item_key
GROUP BY recent.item_key
HAVING max_stores - min_stores >= 5
ORDER BY (max_stores - min_stores) DESC;
```

إنذار مبكر: صنف كان في 20 مخزناً وأصبح في 3 — إشارة نقص وشيك.

## 8. مقارنة runين

```sql
SELECT i.item_code, i.item_name,
       a.status AS status_before, b.status AS status_after,
       a.deterministic_score AS score_before,
       b.deterministic_score AS score_after
FROM run_items a
JOIN run_items b ON b.item_key = a.item_key
JOIN items     i ON i.item_key = a.item_key
WHERE a.run_key = 'wardany/20260827_1321'
  AND b.run_key = 'wardany/20260830_1809'
  AND a.status <> b.status
ORDER BY i.item_code;
```

يستخدم فهرس `idx_run_items_item (item_key, run_key)`. الفائدة الفورية:
بعد أي تعديل على قواعد المطابقة، هذا الاستعلام يُظهر بالضبط أي أصناف
تحسّنت وأيها تراجعت — وهو ما تفعله ملفات
`docs/MATCHING_WRONG_SUBSTITUTIONS_FIX_REPORT.md` اليوم يدوياً.

## 9. أصناف تفشل مطابقتها باستمرار

```sql
SELECT i.item_code, i.item_name,
       COUNT(*)                                            AS runs_seen,
       SUM(CASE WHEN ri.status='no-results' THEN 1 ELSE 0 END) AS no_results,
       SUM(ri.manual_review_required)                      AS flagged
FROM run_items ri
JOIN items i ON i.item_key = ri.item_key
GROUP BY ri.item_key
HAVING runs_seen >= 3 AND no_results = runs_seen
ORDER BY runs_seen DESC;
```

قائمة عمل مباشرة: أصناف لم تُطابَق قط في 3+ runs — إما أن أسماءها تحتاج
تصحيحاً في Excel، أو أن Tawreed لا يبيعها.

## 10. جودة الـ run — بديل `quality_metrics.py`

```sql
SELECT * FROM v_run_summary
WHERE profile_key = 'wardany'
ORDER BY started_at DESC
LIMIT 20;
```

`compute_quality_metrics()` (`src/core/quality/quality_metrics.py:98`)
تقرأ CSV وتعدّ صفاً بصف في Python لـ run واحد. هذا الاستعلام يعطي نفس
النتيجة لآخر 20 run في مسح فهرس واحد — ويجعل رسم اتجاه معدل المطابقة عبر
الزمن ممكناً لأول مرة.

## 11. تغذية الـ run القادم — كاش قابل للاستخدام

```sql
-- المخزن الذي فاز آخر مرة لكل صنف، إن كان حديثاً
SELECT i.item_code, i.item_name,
       ris.store_key, ris.store_product_id,
       ris.discount_percent, r.run_id
FROM run_item_stores ris
JOIN runs  r ON r.run_key  = ris.run_key
JOIN items i ON i.item_key = ris.item_key
WHERE ris.is_winner = 1
  AND r.started_at = (
        SELECT MAX(r2.started_at)
        FROM run_item_stores ris2
        JOIN runs r2 ON r2.run_key = ris2.run_key
        WHERE ris2.item_key = ris.item_key AND ris2.is_winner = 1
      );
```

⚠️ **تحذير مهم**: هذا استعلام تحليلي، **وليس** ترخيصاً لتخطي البحث الحقيقي
في الـ run القادم. الكميات والأسعار في Tawreed تتغير بالساعة. استخدامه
كـ «كاش» لتخطي البحث سيُنتج أوامر شراء بأسعار قديمة وكميات غير متوفرة.

الاستخدام الآمن الوحيد: **ترتيب** المخازن المرشحة (تلميح للأولوية) أو
ضبط `preferred_warehouses`، على أن يبقى التحقق من الكمية والسعر من
Tawreed حياً دائماً.

## 12. اكتشاف مخازن جديدة

```sql
SELECT store_name, first_seen_at
FROM stores
WHERE first_seen_at >= date('now', '-14 days')
ORDER BY first_seen_at DESC;
```

عمود `first_seen_at` في جداول الأبعاد يجعل هذا مجانياً — سبب إضافي
لوجوده.

## واجهة الاستعلامات في الكود

كل هذه الاستعلامات تنتمي إلى `src/core/database/order_runs_queries.py`
كدوال مسمّاة، **لا نصوص SQL متناثرة في طبقة Streamlit**:

```python
def item_price_history(store, item_code: str) -> list[dict]:
    """Return the winning store, price, and discount per run for one item."""

def store_reliability(store, days: int = 90, min_items: int = 20) -> list[dict]:
    """Return stock-rate and average discount per store over a window."""

def suboptimal_winner_choices(store, run_key: str) -> list[dict]:
    """Return items where a higher-discount store was available but unused."""

def run_comparison(store, run_key_a: str, run_key_b: str) -> list[dict]:
    """Return items whose status changed between two runs."""
```

هذا يحقق قاعدة المشروع «Repositories / Data Access Layer — منطق العمل لا
يكتب استعلامات خام» (`docs/project_guidelines.md:223`) ويجعل الاستعلامات
قابلة للاختبار بمعزل عن الواجهة.

## أثر ذلك على Streamlit

`src/ui/views/streamlit_results.py` اليوم:

```python
def command_run_options(command, profile_key):     # السطر 40
    root = ARTIFACTS_DIR / command / profile_key
    runs = sorted((p.name for p in root.iterdir() if p.is_dir()), reverse=True)
```

مسح نظام ملفات في كل رسم للصفحة. يصبح:

```python
def command_run_options(command, profile_key):
    return [r["run_id"] for r in list_runs(store, command, profile_key)]
```

والفائدة الأكبر: تبويب **مقارنة** و**تاريخ الأسعار** يصبحان ممكنين — وهما
مستحيلان حالياً بأي تكلفة معقولة.

الملفات في `artifacts/` تبقى للتنزيل والتشخيص العميق. لا تحذفها.
