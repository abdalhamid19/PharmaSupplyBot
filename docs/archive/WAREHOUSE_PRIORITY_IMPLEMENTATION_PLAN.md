# خطة تنفيذ نظام أولوية المخازن (Preferred Warehouses Priority)

**التاريخ:** 2026-06-26  
**المشروع:** PharmaSupplyBot  
**الميزة:** ترتيب أولوية المخازن عند تساوي الخصم

---

## 1. فهم المتطلبات

### 1.1 المتطلب الأساسي

**الهدف:** عند تساوي الخصم بين عدة مخازن، يتم تفضيل المخازن حسب قائمة أولويات محددة.

**قائمة الأولويات (من الأعلى للأقل):**
1. شركه البركه (الجيزه)
2. شركه الشفاء ميدكو - الريحان سابقا (الجيزه)
3. شركه الفا فارما (الجيزه)
4. شركه مصر مديكال (الجيزه)
5. شركه نيو سيدرا (القليوبيه)
6. شركه الريان (القاهره)

**السلوك المطلوب:**
- إذا كان هناك مخزنان بخصم 25%، واحد من "البركه" والآخر من "الريان" → اختر "البركه"
- إذا كان هناك مخزن "الريان" بخصم 30% ومخزن "البركه" بخصم 25% → اختر "الريان" (الخصم الأعلى)
- الأولوية تُطبق **فقط عند التساوي في الخصم**

### 1.2 الافتراضات

1. ✅ قائمة الأولويات ثابتة ويمكن تخزينها في `config.yaml`
2. ✅ المطابقة ستكون عبر اسم المخزن (`storeName`)
3. ✅ المطابقة يجب أن تكون مرنة (fuzzy) لتحمّل اختلافات طفيفة في التسمية
4. ✅ المخازن غير المدرجة في القائمة لها أولوية أقل من جميع المخازن المدرجة

### 1.3 نقاط الغموض المحتملة

❓ **سؤال 1:** هل الأولوية تُطبق في جميع أوضاع الاختيار (first_available, max_available, max_discount)؟
- **الافتراض:** نعم، في جميع الأوضاع عند تساوي المعيار الأساسي

❓ **سؤال 2:** ما هو تعريف "التساوي في الخصم"؟ نفس النسبة تماماً أم ضمن tolerance؟
- **الافتراض:** ضمن tolerance صغير جداً (0.001%) لتجنب مشاكل floating-point

❓ **سؤال 3:** كيف نتعامل مع المخازن التي أسماؤها لا تطابق القائمة؟
- **الافتراض:** تُعطى أولوية منخفضة (infinity) وتُختار بعد جميع المخازن المفضلة

---

## 2. التحليل التقني

### 2.1 الكود الحالي

#### أ. موقع منطق الاختيار

**الملف:** `src/tawreed/tawreed_store_selection.py`

**الدالة الرئيسية:**
```python
def _select_choice(choices: list[StoreChoice], mode: str) -> StoreChoice:
    if mode == "first_available":
        return choices[0]  # ← يأخذ أول واحد فقط
    if mode == "max_available":
        return max(choices, key=lambda c: (c.available_quantity, c.discount_percent))
    if mode == "max_discount":
        return max(choices, key=lambda c: (c.discount_percent, c.available_quantity))
```

**التحليل:**
- ✅ يستخدم `max()` مع `key` tuple
- ✅ tuple comparison في Python: يقارن العنصر الأول، ثم الثاني عند التساوي
- ✅ يمكن إضافة عنصر ثالث للـ tuple هو priority!

#### ب. هيكل البيانات

```python
@dataclass(frozen=True)
class StoreChoice:
    index: int
    store: dict[str, Any]
    identity: str
    available_quantity: int
    discount_percent: float
    # ← يمكن إضافة priority_score هنا
```

### 2.2 استراتيجية التنفيذ

#### الخيار 1: إضافة priority_score إلى StoreChoice ✅ (المفضل)

**المزايا:**
- 🟢 بسيط ونظيف
- 🟢 يعمل مع جميع الأوضاع تلقائياً
- 🟢 لا يغير واجهات الدوال الموجودة

**العيوب:**
- 🔴 يتطلب تعديل dataclass

**التنفيذ:**
```python
@dataclass(frozen=True)
class StoreChoice:
    ...
    priority_score: int  # 1 = highest priority, 999 = unknown store

def _select_choice(choices, mode):
    if mode == "max_discount":
        return max(choices, key=lambda c: (c.discount_percent, -c.priority_score, c.available_quantity))
        # ↑ negative priority_score لأن الأقل = الأفضل
```

#### الخيار 2: sort مخصص قبل الاختيار

**المزايا:**
- 🟢 لا يغير StoreChoice

**العيوب:**
- 🔴 يتطلب sorting إضافي
- 🔴 أقل كفاءة

---

## 3. التصميم المفصل

### 3.1 الإعدادات في config.yaml

```yaml
warehouse_strategy:
  mode: "max_discount"
  min_discount_percent: 0
  
  # NEW: Preferred warehouses (highest to lowest priority)
  preferred_warehouses:
    - "شركه البركه (الجيزه)"
    - "شركه الشفاء ميدكو - الريحان سابقا (الجيزه)"
    - "شركه الفا فارما (الجيزه)"
    - "شركه مصر مديكال (الجيزه)"
    - "شركه نيو سيدرا (القليوبيه)"
    - "شركه الريان (القاهره)"
```

### 3.2 دالة حساب الأولوية

```python
def _calculate_priority_score(store_name: str, preferred_list: list[str]) -> int:
    """
    Calculate priority score for a warehouse.
    Lower score = higher priority.
    
    Returns:
        1-based index if found in preferred list, 999 if not found.
    """
    normalized_name = _normalize_store_name(store_name)
    
    for index, preferred_name in enumerate(preferred_list, start=1):
        normalized_preferred = _normalize_store_name(preferred_name)
        if _stores_match(normalized_name, normalized_preferred):
            return index
    
    return 999  # Unknown store = lowest priority

def _normalize_store_name(name: str) -> str:
    """Normalize store name for comparison."""
    import re
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)  # Multiple spaces → single space
    name = name.lower()
    return name

def _stores_match(name1: str, name2: str) -> bool:
    """Check if two store names match (exact or fuzzy)."""
    if name1 == name2:
        return True
    
    # Fuzzy: check if one contains the other (for variations)
    if name1 in name2 or name2 in name1:
        return True
    
    # Can add more sophisticated fuzzy matching if needed
    return False
```

### 3.3 تعديل StoreChoice

```python
@dataclass(frozen=True)
class StoreChoice:
    index: int
    store: dict[str, Any]
    identity: str
    available_quantity: int
    discount_percent: float
    priority_score: int = 999  # Default: unknown store
```

### 3.4 تعديل _store_choice

```python
def _store_choice(index: int, store: dict[str, Any], config=None) -> StoreChoice:
    priority = 999  # Default
    
    if config and config.warehouse_strategy.get("preferred_warehouses"):
        store_name_value = store_name(store)  # Get store name
        priority = _calculate_priority_score(
            store_name_value,
            config.warehouse_strategy["preferred_warehouses"]
        )
    
    return StoreChoice(
        index=index,
        store=store,
        identity=_store_identity(index, store),
        available_quantity=_available_quantity(store),
        discount_percent=_discount_percent(store),
        priority_score=priority,
    )
```

### 3.5 تعديل _select_choice

```python
def _select_choice(choices: list[StoreChoice], mode: str) -> StoreChoice:
    if mode == "first_available":
        # Sort by priority, then take first
        return min(choices, key=lambda c: (c.priority_score, c.index))
    
    if mode == "max_available":
        # Max quantity, then priority, then discount
        return max(choices, key=lambda c: (
            c.available_quantity,
            -c.priority_score,  # Negative: lower is better
            c.discount_percent
        ))
    
    if mode == "max_discount":
        # Max discount, then priority, then quantity
        return max(choices, key=lambda c: (
            c.discount_percent,
            -c.priority_score,  # Negative: lower is better
            c.available_quantity
        ))
    
    raise ValueError(f"Unknown warehouse strategy mode: {mode}")
```

---

## 4. خطة التنفيذ (Milestones)

### Phase 1: التحضير والتحليل ✅

- [x] قراءة project_guidelines
- [x] قراءة starting_prompt
- [x] فهم الكود الحالي
- [x] تحديد الاستراتيجية الأمثل
- [x] كتابة الخطة المفصلة

### Phase 2: التنفيذ الأساسي

**Milestone 2.1: إضافة الإعدادات**
- [ ] إضافة `preferred_warehouses` في `config.yaml`
- [ ] إضافة `preferred_warehouses` في `config.example.yaml`
- [ ] التحقق: قراءة القيمة من config

**Milestone 2.2: تعديل StoreChoice**
- [ ] إضافة حقل `priority_score` في dataclass
- [ ] تعديل `_store_choice` لحساب الأولوية
- [ ] التحقق: unit test لـ StoreChoice

**Milestone 2.3: دوال المطابقة**
- [ ] إنشاء `_calculate_priority_score`
- [ ] إنشاء `_normalize_store_name`
- [ ] إنشاء `_stores_match`
- [ ] التحقق: unit tests للمطابقة

**Milestone 2.4: تعديل منطق الاختيار**
- [ ] تعديل `_select_choice` لاستخدام priority
- [ ] تمرير config إلى `_store_choice`
- [ ] التحقق: unit tests لجميع الأوضاع

### Phase 3: التكامل

**Milestone 3.1: تمرير Config**
- [ ] تتبع استدعاءات `_store_choice` في الكود
- [ ] تمرير bot.config أو config من المستدعي
- [ ] التحقق: لا import cycles

**Milestone 3.2: اختبارات شاملة**
- [ ] اختبار: مخزنان بنفس الخصم، أحدهما مفضل
- [ ] اختبار: مخزنان، الأعلى خصماً غير مفضل
- [ ] اختبار: مخزن غير موجود في القائمة
- [ ] اختبار: قائمة فارغة (no preferred)
- [ ] اختبار: اسم مخزن بحروف مختلفة

### Phase 4: التحقق النهائي

**Milestone 4.1: تشغيل جميع الاختبارات**
- [ ] `python -m unittest discover -s tests`
- [ ] التأكد: 0 failures

**Milestone 4.2: rule_audit**
- [ ] `python tools/rule_audit.py`
- [ ] إصلاح أي مخالفات

**Milestone 4.3: التوثيق**
- [ ] تحديث README إذا لزم
- [ ] كتابة markdown نهائي للميزة

---

## 5. معايير النجاح (Verifiable Goals)

### ✅ Goal 1: الإعدادات
```python
from src.core.config.config import load_config
config = load_config(Path("config.yaml"))
assert "preferred_warehouses" in config.warehouse_strategy
assert len(config.warehouse_strategy["preferred_warehouses"]) == 6
```

### ✅ Goal 2: المطابقة
```python
assert _calculate_priority_score("شركه البركه (الجيزه)", preferred) == 1
assert _calculate_priority_score("شركه الريان (القاهره)", preferred) == 6
assert _calculate_priority_score("شركه غير معروفة", preferred) == 999
```

### ✅ Goal 3: الاختيار
```python
store1 = StoreChoice(..., discount_percent=25.0, priority_score=1)  # البركه
store2 = StoreChoice(..., discount_percent=25.0, priority_score=6)  # الريان
chosen = _select_choice([store1, store2], "max_discount")
assert chosen.priority_score == 1  # البركه
```

### ✅ Goal 4: الأولوية لا تتجاوز الخصم
```python
store1 = StoreChoice(..., discount_percent=25.0, priority_score=1)  # البركه 25%
store2 = StoreChoice(..., discount_percent=30.0, priority_score=6)  # الريان 30%
chosen = _select_choice([store1, store2], "max_discount")
assert chosen.priority_score == 6  # الريان لأن 30% > 25%
```

---

## 6. المخاطر والتحديات

### 6.1 المخاطر المحتملة

#### خطر 1: اختلاف أسماء المخازن
**الوصف:** قد تأتي أسماء المخازن من API بصيغة مختلفة قليلاً  
**التخفيف:** استخدام fuzzy matching مع normalization  
**الاختبار:** جمع أسماء فعلية من API وفحصها

#### خطر 2: تأثير على الأداء
**الوصف:** حساب priority لكل مخزن قد يؤثر على السرعة  
**التخفيف:** الحساب بسيط (loop على 6 عناصر فقط)  
**القياس:** قياس الوقت قبل وبعد

#### خطر 3: import cycles
**الوصف:** تمرير config قد يسبب import cycles  
**التخفيف:** تمرير config كـ parameter، لا import  
**التحقق:** فحص imports بعد التنفيذ

### 6.2 الحلول البديلة (Fallback)

إذا فشل الحل الأساسي:
- **Plan B:** استخدام decorator pattern بدلاً من تعديل dataclass
- **Plan C:** إنشاء wrapper function حول `_select_choice`

---

## 7. الأسئلة المفتوحة

### ❓ سؤال 1: هل نحتاج GUI controls؟
- **السياق:** هل يجب أن يتحكم المستخدم في القائمة من GUI؟
- **الافتراض الحالي:** لا، القائمة ثابتة في config.yaml
- **التأثير:** إذا نعم، نحتاج تعديلات في streamlit_order_form.py

### ❓ سؤال 2: هل نطبق على single-store أيضاً؟
- **السياق:** المنتجات ذات المخزن الواحد
- **الافتراض الحالي:** لا تأثير (مخزن واحد فقط، لا اختيار)
- **التأثير:** لا شيء

### ❓ سؤال 3: هل نسجل اختيار الأولوية في logs؟
- **السياق:** هل نُظهر "Selected store X due to priority"؟
- **الافتراض الحالي:** نعم، سيكون مفيداً للتتبع
- **التأثير:** إضافة log statement في _select_choice

---

## 8. الخلاصة

### 8.1 الحل المقترح

**النهج:** إضافة `priority_score` إلى `StoreChoice` واستخدامه في tuple comparison

**التعقيد:** منخفض (< 100 سطر كود جديد)

**الملفات المتأثرة:**
1. `config.yaml` + `config.example.yaml`
2. `src/tawreed/tawreed_store_selection.py`
3. `tests/test_tawreed_store_selection.py` (جديد أو تحديث)

**الاختبارات:** ~10 اختبارات جديدة

### 8.2 الخطوات التالية

1. ✅ مراجعة الخطة مع المستخدم
2. ⏳ الموافقة على النهج
3. ⏳ البدء في التنفيذ Phase 2

---

**تم إعداد الخطة بواسطة:** Kiro AI Assistant  
**الحالة:** ✅ جاهزة للمراجعة والموافقة  
**الخطوة التالية:** انتظار تأكيد المستخدم للبدء في التنفيذ
