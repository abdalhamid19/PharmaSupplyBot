# خطة إعادة الهيكلة (Refactoring Plan)

## نظرة عامة
يحتوي مشروع PharmaSupplyBot على كود جيد التنظيم بشكل عام، ولكن هناك بعض المناطق التي تحتاج إلى إعادة هيكلة لتحسين الصيانة والقابلية للتوسع.

---

## 🔴 أولوية عالية (High Priority)

### 1. فئة TawreedBot الكبيرة (src/tawreed/tawreed.py)
**المشكلة:**
- يحتوي الملف على 976 سطر
- الفئة TawreedBot تحتوي على مسؤوليات كثيرة (Authentication, Ordering, Matching, API handling)
- صعب الصيانة والاختبار

**الحل المقترح:**
```
src/tawreed/
├── tawreed_bot.py           # Main bot coordinator (smaller)
├── tawreed_auth_flow.py     # Authentication logic
├── tawreed_order_flow.py    # Order processing logic
├── tawreed_match_flow.py    # Product matching logic
├── tawreed_api_flow.py      # API execution logic
└── tawreed_error_handler.py # Error handling and diagnostics
```

**الفوائد:**
- فصل المسؤوليات (Single Responsibility Principle)
- سهولة الاختبار الوحدوي
- تحسين قابلية القراءة

---

### 2. CLI Order Module (src/cli/cli_order.py)
**المشكلة:**
- 478 سطر من الكود
- يحتوي على منطق معقد للتوازي (parallel processing)
- وظائف متعددة مختلطة (item loading, filtering, worker management)

**الحل المقترح:**
```
src/cli/order/
├── order_coordinator.py     # Main order coordination
├── order_item_loader.py     # Item loading and filtering
├── order_worker_manager.py  # Parallel worker management
├── order_artifact_merger.py # Artifact merging logic
└── order_error_handler.py   # Order-specific error handling
```

**الفوائد:**
- فصل منطق التوازي عن منطق الطلب
- سهولة إضافة ميزات جديدة
- تحسين إعادة استخدام الكود

---

### 3. Database Manager Hardcoded Credentials (src/core/database.py)
**المشكلة:**
- بيانات الاتصال مشفرة داخل الكود (Lines 21-25)
- مخاطر أمنية
- صعب التغيير بين البيئات

**الحل المقترح:**
```python
# إزالة الثوابت المشفرة
# DEFAULT_HOST = "mahrousdb-27867.j77.aws-eu-central-1.cockroachlabs.cloud"
# DEFAULT_PORT = 26257
# DEFAULT_DATABASE = "defaultdb"
# DEFAULT_USER = "abdalhamid"

# الاعتماد فقط على البيئة المتغيرات
self.host = host or os.getenv("DB_HOST")
self.port = port or int(os.getenv("DB_PORT", "26257"))
self.database = database or os.getenv("DB_NAME", "defaultdb")
self.user = user or os.getenv("DB_USER")
```

**الفوائد:**
- تحسين الأمان
- سهولة التبديل بين البيئات (dev/staging/prod)
- منع تسريب البيانات الحساسة

---

## 🟡 أولوية متوسطة (Medium Priority)

### 4. Drug Matching Pipeline (src/core/drug_matching/pipeline.py)
**المشكلة:**
- 464 سطر
- منطق معقد للـ AI matching
- فصل ضعيف بين المراحل

**الحل المقترح:**
```
src/core/drug_matching/
├── pipeline.py              # Main pipeline coordinator
├── matching_phase.py        # Algorithmic matching phase
├── ai_verification_phase.py # AI verification phase
├── ai_search_phase.py       # AI search phase
├── ai_review_phase.py       # AI review phase
└── result_formatter.py      # Result formatting and saving
```

**الفوائد:**
- فصل واضح بين مراحل المطابقة
- سهولة تعطيل/تفعيل مراحل معينة
- تحسين قابلية الاختبار

---

### 5. تكرار الكود في CLI Parsers
**المشكلة:**
- 11 ملف parser مختلف
- تكرار في منطق تحليل الوسائط (argument parsing)
- صعب إضافة خيارات جديدة

**الحل المقترح:**
```
src/cli/parser/
├── base_parser.py           # Base parser with common options
├── auth_parser.py           # Auth-specific options
├── order_parser.py          # Order-specific options
├── export_parser.py         # Export-specific options
└── parser_factory.py        # Parser assembly
```

**الفوائد:**
- تقليل التكرار (DRY principle)
- سهولة إضافة خيارات مشتركة
- تحسين الصيانة

---

### 6. Manual Review System
**المشكلة:**
- ملفات متعددة مرتبطة بـ manual review
- منطق معقد لتخزين واسترجاع القرارات
- عدم وضوح العلاقة بين المكونات

**الحل المقترح:**
```
src/core/manual_review/
├── review_store.py          # Main storage interface
├── review_corrections.py     # Correction handling
├── review_candidates.py     # Candidate management
├── review_runtime.py        # Runtime cache
└── review_sql_store.py      # SQL implementation
```

**الفوائد:**
- تنظيم أفضل للعلاقات
- سهولة إضافة طرق تخزين جديدة
- تحسين الوضوح

---

## 🟢 أولوية منخفضة (Low Priority)

### 7. Configuration System
**المشكلة:**
- ملفات config متعددة (config.py, config_factory.py, config_models.py)
- منطق معقد للتحميل والتحقق

**الحل المقترح:**
```
src/core/config/
├── config_loader.py         # Main loading logic
├── config_validator.py      # Validation logic
├── config_models.py         # Data models
└── config_defaults.py       # Default values
```

**الفوائد:**
- فصل منطق التحميل عن التحقق
- سهولة إضافة مصادر config جديدة
- تحسين رسائل الخطأ

---

### 8. Utils Functions
**المشكلة:**
- دوال مساعدة متناثرة
- عدم وضوح العلاقات

**الحل المقترح:**
```
src/core/utils/
├── excel_utils.py           # Excel-specific utilities
├── browser_utils.py         # Browser-specific utilities
├── text_utils.py            # Text processing utilities
└── chunking_utils.py        # Chunking logic
```

**الفوائد:**
- تنظيم أفضل
- سهولة إعادة الاستخدام
- تحسين الوثائق

---

## 📋 خطوات التنفيذ المقترحة

### المرحلة 1: الإصلاحات الأمنية (1-2 أيام)
1. إزالة البيانات المشفرة من Database Manager
2. التأكد من أن جميع البيانات الحساسة من البيئة المتغيرات
3. تحديث الوثائق

### المرحلة 2: الفئات الكبيرة (3-5 أيام)
1. تقسيم TawreedBot
2. تقسيم CLI Order Module
3. كتابة الاختبارات للوحدات الجديدة

### المرحلة 3: تحسين البنية (2-3 أيام)
1. إعادة تنظيم Drug Matching Pipeline
2. توحيد CLI Parsers
3. تنظيم Manual Review System

### المرحلة 4: التحسينات النهائية (1-2 أيام)
1. تحسين Configuration System
2. تنظيم Utils Functions
3. تحديث الوثائق والتعليقات

---

## 🎯 المعايير (Success Criteria)

- ✅ تقليل حجم الملفات الكبيرة إلى < 500 سطر
- ✅ فصل المسؤوليات بشكل واضح
- ✅ تحسين تغطية الاختبارات
- ✅ إزالة جميع البيانات الحساسة المشفرة
- ✅ تحسين الوثائق والتعليقات
- ✅ الحفاظ على التوافق مع الوظائف الحالية

---

## ⚠️ ملاحظات هامة

1. **التدرجية:** تنفيذ التغييرات تدريجياً مع اختبار كل مرحلة
2. **الاختبارات:** كتابة اختبارات قبل إعادة الهيكلة (TDD)
3. **التوافق:** التأكد من عدم كسر الوظائف الحالية
4. **الوثائق:** تحديث الوثائق مع كل تغيير
5. **مراجعة الكود:** مراجعة التغييرات قبل الدمج

---

## 📚 مراجع إضافية

- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [Refactoring by Martin Fowler](https://refactoring.com/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
