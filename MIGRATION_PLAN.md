# خطة الانتقال من SQLite إلى CockroachDB Cloud

## 📊 الوضع الحالي

### قاعدة البيانات الحالية (SQLite)
- **المسار**: `data/manual_review/manual_review.sqlite3`
- **الحجم**: 12 KB
- **عدد السجلات**: 6 سجلات
- **الجدول الرئيسي**: `manual_review_decisions`
- **آخر تحديث**: 19 يونيو 2026

### بنية الجدول
```sql
CREATE TABLE manual_review_decisions (
    item_code_key TEXT NOT NULL,           -- مفتاح الكود (منظم)
    item_name_key TEXT NOT NULL,           -- مفتاح الاسم (منظم)
    item_code TEXT NOT NULL,               -- كود الصنف الأصلي
    item_name TEXT NOT NULL,               -- اسم الصنف الأصلي
    approved INTEGER NOT NULL,             -- 1 = موافق، 0 = مرفوض
    manual_decision TEXT NOT NULL DEFAULT '',
    correct_store_product_id TEXT NOT NULL DEFAULT '',
    correct_product_name TEXT NOT NULL DEFAULT '',
    correct_product_name_ar TEXT NOT NULL DEFAULT '',
    correct_query TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_code_key, item_name_key)
)
```

### استخدامات `ManualReviewStore` في الكود
تم العثور على 42 استخدام في 14 ملف:
- `src/core/manual_review_store.py` (الملف الرئيسي)
- `src/core/manual_review_runtime.py`
- `src/core/manual_review_removal.py`
- `src/tawreed/tawreed_order_run_artifacts.py`
- `src/ui/streamlit_manual_review*.py` (6 ملفات)
- `tests/test_manual_review*.py` (7 ملفات)

---

## 🎯 الهدف المطلوب

### معلومات CockroachDB Cloud
```
الحساب: abdalhamid@gmail.com
المستخدم: abdalhamid
كلمة المرور: <PASSWORD_FROM_SECURE_CHANNEL>
الكلستر: mahrousdb
المضيف: mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud
المنطقة: AWS EU (Frankfurt)
النسخة: CockroachDB v25.4.10
قاعدة البيانات: defaultdb

Connection String:
postgresql://abdalhamid:<PASSWORD>@mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full
```

### الفوائد المتوقعة
1. ✅ **مشاركة البيانات**: قاعدة بيانات مركزية مشتركة بين عدة أجهزة
2. ✅ **النسخ الاحتياطي**: نسخ تلقائي في السحابة
3. ✅ **الأداء**: قاعدة موزعة عالية التوافر
4. ✅ **التوسع**: إمكانية التوسع مستقبلاً
5. ✅ **الموثوقية**: عدم فقدان البيانات عند تلف القرص المحلي

---

## 📋 خطة التنفيذ (7 مراحل)

### المرحلة 1: الإعداد والتحقق من الاتصال ⚙️

#### 1.1 تحديث ملف `.env`
```bash
# إضافة بيانات CockroachDB
DB_HOST=mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud
DB_PORT=26257
DB_NAME=defaultdb
DB_USER=abdalhamid
DB_PASSWORD=your-db-password-here
DB_SSLMODE=require
```

#### 1.2 التأكد من المكتبات المطلوبة
- ✅ `psycopg2-binary>=2.9.0` (موجودة بالفعل في `requirements.txt`)

#### 1.3 اختبار الاتصال
```python
# إنشاء سكريبت test_cockroachdb_connection.py
python test_cockroachdb_connection.py
```

**النتيجة المتوقعة**: اتصال ناجح وعرض نسخة CockroachDB

---

### المرحلة 2: إنشاء الجدول في CockroachDB 🗄️

#### 2.1 كتابة SQL Schema متوافق
```sql
CREATE TABLE IF NOT EXISTS manual_review_decisions (
    item_code_key STRING NOT NULL,
    item_name_key STRING NOT NULL,
    item_code STRING NOT NULL,
    item_name STRING NOT NULL,
    approved INT NOT NULL,
    manual_decision STRING NOT NULL DEFAULT '',
    correct_store_product_id STRING NOT NULL DEFAULT '',
    correct_product_name STRING NOT NULL DEFAULT '',
    correct_product_name_ar STRING NOT NULL DEFAULT '',
    correct_query STRING NOT NULL DEFAULT '',
    run_id STRING NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_code_key, item_name_key)
);

CREATE INDEX IF NOT EXISTS idx_updated_at ON manual_review_decisions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_item_code ON manual_review_decisions(item_code);
```

**الفروقات عن SQLite**:
- `TEXT` → `STRING`
- `INTEGER` → `INT`
- إضافة فهارس للأداء

#### 2.2 إنشاء سكريبت الإعداد
```bash
python tools/init_cockroachdb_schema.py
```

---

### المرحلة 3: ترحيل البيانات الموجودة 📦

#### 3.1 استخراج البيانات من SQLite
```python
# إنشاء export_sqlite_data.py
- قراءة جميع السجلات من SQLite
- حفظها في ملف JSON مؤقت
```

#### 3.2 استيراد البيانات إلى CockroachDB
```python
# إنشاء import_to_cockroachdb.py
- قراءة البيانات من JSON
- إدراجها في CockroachDB باستخدام batch insert
- التحقق من عدد السجلات
```

#### 3.3 التحقق من صحة الترحيل
```sql
-- مقارنة العدد
SELECT COUNT(*) FROM manual_review_decisions;

-- مقارنة عينة من البيانات
SELECT * FROM manual_review_decisions ORDER BY updated_at DESC LIMIT 5;
```

---

### المرحلة 4: تعديل `ManualReviewStore` 🔧

#### 4.1 إنشاء adapter جديد
```python
# src/core/manual_review_store_cockroachdb.py
class ManualReviewStoreCockroachDB:
    """CockroachDB implementation of ManualReviewStore."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._init_schema()
    
    def upsert(self, decision: ManualReviewDecision) -> None:
        # UPSERT query compatible with CockroachDB
        ...
    
    def lookup(self, item_code: str, item_name: str) -> ManualReviewDecision | None:
        ...
    
    def delete(self, item_code: str, item_name: str) -> None:
        ...
    
    def list_decisions(self) -> list[ManualReviewDecision]:
        ...
```

#### 4.2 تعديل `manual_review_store.py`
```python
# إضافة factory pattern لاختيار التطبيق
def get_manual_review_store(use_cloud: bool = True) -> ManualReviewStore:
    if use_cloud and os.getenv("DB_PASSWORD"):
        return ManualReviewStoreCockroachDB(get_db_manager())
    else:
        return ManualReviewStoreSQLite(DEFAULT_MANUAL_REVIEW_DB)
```

#### 4.3 تحديث SQL statements
```python
# src/core/manual_review_store_sql_cockroachdb.py
# تحويل queries من SQLite إلى CockroachDB dialect
```

**الفروقات الرئيسية**:
- `PRAGMA` لا يعمل في CockroachDB → إزالته
- `current_timestamp` يعمل بنفس الطريقة ✅
- `UPSERT` syntax مختلف قليلاً

---

### المرحلة 5: تحديث الملفات المستخدمة 📝

#### 5.1 تحديث استدعاءات ManualReviewStore
قائمة الملفات التي تحتاج تعديل (14 ملف):

```python
# قبل:
store = ManualReviewStore()

# بعد:
store = get_manual_review_store()
```

**الملفات**:
1. `src/core/manual_review_runtime.py`
2. `src/core/manual_review_removal.py`
3. `src/tawreed/tawreed_order_run_artifacts.py`
4. `src/ui/streamlit_manual_review.py`
5. `src/ui/streamlit_manual_review_page_candidates.py`
6. `src/ui/streamlit_manual_review_page_form.py`
7. `src/ui/streamlit_manual_review_page_saved.py`
8. `src/ui/streamlit_manual_review_rows.py`

#### 5.2 تحديث Tests
- تحديث 7 ملفات test لدعم كلا التطبيقين
- إضافة اختبارات CockroachDB منفصلة

---

### المرحلة 6: الاختبار الشامل ✅

#### 6.1 اختبار الوظائف الأساسية
```bash
# تشغيل جميع الاختبارات
python -m unittest discover -s tests -q

# اختبار محدد
python -m unittest tests.test_manual_review_store
```

#### 6.2 اختبار سيناريوهات حقيقية
1. ✅ حفظ قرار جديد
2. ✅ البحث عن قرار موجود
3. ✅ تحديث قرار قديم
4. ✅ حذف قرار
5. ✅ عرض جميع القرارات

#### 6.3 اختبار Streamlit UI
```bash
python -m streamlit run streamlit_app.py
```
- اختبار صفحة Manual Review
- التحقق من عرض البيانات من CockroachDB

#### 6.4 اختبار CLI
```bash
python run.py order --excel "data/input/order_items/test.xlsx" --profile wardany --limit 2 --ai
```

---

### المرحلة 7: النشر والتوثيق 📚

#### 7.1 تحديث README.md
```markdown
## قاعدة البيانات السحابية

يستخدم المشروع الآن CockroachDB Cloud كقاعدة بيانات مشتركة لحفظ قرارات المراجعة اليدوية.

### الإعداد
1. انسخ `.env.example` إلى `.env`
2. أضف `DB_PASSWORD` الخاص بك
3. سيتصل البوت تلقائياً بالسحابة

### العودة إلى SQLite (اختياري)
إذا أردت استخدام SQLite محلياً، احذف `DB_PASSWORD` من `.env`
```

#### 7.2 إنشاء وثيقة Migration Guide
```markdown
# Migration Guide: SQLite → CockroachDB

## للمستخدمين الحاليين
...
```

#### 7.3 إنشاء backup script
```bash
# tools/backup_manual_reviews.py
python tools/backup_manual_reviews.py --output backup_YYYYMMDD.json
```

#### 7.4 Cleanup (اختياري)
```bash
# نقل SQLite القديم إلى أرشيف
mkdir -p data/manual_review/archive
mv data/manual_review/manual_review.sqlite3 data/manual_review/archive/manual_review_backup_20260619.sqlite3
```

---

## 📁 ملفات جديدة سيتم إنشاؤها

```
PharmaSupplyBot/
├── tools/
│   ├── init_cockroachdb_schema.py       # إنشاء الجدول
│   ├── export_sqlite_data.py            # تصدير من SQLite
│   ├── import_to_cockroachdb.py         # استيراد إلى CockroachDB
│   ├── test_cockroachdb_connection.py   # اختبار الاتصال
│   └── backup_manual_reviews.py         # نسخ احتياطي
├── src/core/
│   ├── manual_review_store_cockroachdb.py        # تطبيق CockroachDB
│   └── manual_review_store_sql_cockroachdb.py    # SQL queries
├── tests/
│   └── test_manual_review_store_cockroachdb.py   # اختبارات CockroachDB
├── MIGRATION_PLAN.md                    # هذا الملف
└── MIGRATION_GUIDE.md                   # دليل للمستخدمين
```

---

## ⚠️ نقاط مهمة ومخاطر

### الأمان
- ✅ استخدام متغيرات البيئة لكلمة المرور
- ✅ `sslmode=verify-full` للاتصال الآمن
- ⚠️ عدم حفظ كلمة المرور في الكود

### التوافق
- ✅ CockroachDB متوافق 99% مع PostgreSQL
- ⚠️ بعض features مثل `PRAGMA` غير مدعومة
- ✅ pool connections جاهز في `database.py`

### الأداء
- ✅ إضافة indexes على الأعمدة المهمة
- ✅ استخدام connection pooling
- ⚠️ الاتصال عبر الإنترنت أبطأ من المحلي (latency)

### Rollback Plan
إذا حدثت مشاكل:
1. الاحتفاظ بنسخة SQLite الأصلية
2. تعطيل `DB_PASSWORD` من `.env`
3. سيعود البوت تلقائياً لـ SQLite

---

## 📊 جدول زمني متوقع

| المرحلة | الوقت المتوقع | المتطلبات |
|---------|---------------|-----------|
| 1. الإعداد | 15 دقيقة | اختبار الاتصال |
| 2. إنشاء Schema | 10 دقائق | SQL script |
| 3. ترحيل البيانات | 5 دقائق | 6 سجلات فقط |
| 4. تعديل ManualReviewStore | 30 دقيقة | coding |
| 5. تحديث الملفات | 20 دقيقة | 14 ملف |
| 6. الاختبار | 30 دقيقة | شامل |
| 7. التوثيق | 20 دقيقة | README |
| **المجموع** | **~2 ساعة** | - |

---

## ✅ Checklist للتنفيذ

### الإعداد
- [ ] تحديث `.env` بمعلومات CockroachDB
- [ ] اختبار الاتصال
- [ ] التأكد من `psycopg2-binary`

### قاعدة البيانات
- [ ] إنشاء schema في CockroachDB
- [ ] تصدير بيانات SQLite
- [ ] استيراد البيانات إلى CockroachDB
- [ ] التحقق من صحة البيانات

### الكود
- [ ] إنشاء `ManualReviewStoreCockroachDB`
- [ ] إنشاء factory pattern
- [ ] تحديث 14 ملف بالاستدعاء الجديد
- [ ] تحديث SQL statements

### الاختبار
- [ ] unit tests تعمل
- [ ] integration tests تعمل
- [ ] Streamlit UI يعمل
- [ ] CLI يعمل
- [ ] اختبار حقيقي بملف Excel

### التوثيق
- [ ] تحديث README
- [ ] كتابة Migration Guide
- [ ] إنشاء backup script
- [ ] نقل SQLite القديم للأرشيف

---

## 🎉 النتيجة النهائية

بعد التنفيذ:
1. ✅ جميع البيانات محفوظة في CockroachDB Cloud
2. ✅ يمكن الوصول للبيانات من أي جهاز
3. ✅ نسخ احتياطي تلقائي
4. ✅ البوت يعمل بنفس الوظائف السابقة
5. ✅ إمكانية العودة لـ SQLite إذا لزم الأمر

---

## 📞 الخطوة التالية

**هل تريد البدء بالتنفيذ؟**

يمكنني البدء بـ:
1. إنشاء سكريبت اختبار الاتصال
2. إنشاء schema SQL
3. كتابة كود الترحيل

أم تريد مراجعة الخطة أولاً؟
