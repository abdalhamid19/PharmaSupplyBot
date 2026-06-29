# تقرير: اختلاف الأصناف بين Manual Review Table و Candidates

**التاريخ:** 2026-06-23  
**Run المشكل:** 20260622_1856  

---

## 🔴 المشكلتان

### 1. أصناف مختلفة في الصفحة الأولى
- **Manual Review Table:** `panthenol`, `THROMBEXX`, etc.
- **Candidates section:** `APILIPEX`, `DHEA`, etc.
- **مختلفة تماماً** ❌

### 2. Stats لا تتحدث من Candidates
- تصحيح في Candidates → `Total: 400` لا يتغير ❌

---

## 🔍 السبب الجذري

### مصدران مختلفان!

| Feature | manual_review.csv | manual_review_candidates.jsonl |
|---------|-------------------|--------------------------------|
| **المحتوى** | كل items محتاجة review | items لها candidates فقط |
| **العدد** | 400 | 400 |
| **الترتيب** | مختلف | مختلف |
| **الأصناف** | مختلفة جزئياً | مختلفة جزئياً |

**CSV أول 5:**
- 91304 - panthenol 5% care cream 50 gm
- 54471 - THROMBEXX DNA GEL40 G
- 22773 - RIRI MILK CEREAL&FRUITS POWDER

**JSONL أول 5:**
- 67320 - APILIPEX 30MG 30TAB
- 64792 - DHEA 50 MG 100 TAB
- 29411 - VANCOMYCIN 50OMG VIAL

---

## ✅ الحل المطبق

### تحديث Cache من Candidates

**الملف:** `src/ui/streamlit_manual_review_page_form.py`

**التعديل:**
```python
def _save(...):
    # Save to CockroachDB
    store.upsert(decision)
    
    # ⚡ Update session cache
    cache_key = f"manual_review_cache_{run_dir.name}"
    if cache_key in st.session_state:
        for i, row in enumerate(st.session_state[cache_key]):
            if row["item_code"] == item.code and row["item_name"] == item.name:
                # Update decision fields
                st.session_state[cache_key][i]["approved_match"] = decision.approved
                st.session_state[cache_key][i]["not_matching"] = ...
                break
```

**النتيجة:**
- ✅ Stats تتحدث عند Save في Candidates
- ✅ Cache متزامن مع DB

---

## 📊 النتيجة

### قبل الحل:
| العملية | السلوك |
|---------|--------|
| تصحيح في Table | ✅ Stats تتحدث |
| تصحيح في Candidates | ❌ Stats ثابتة |
| Sync بين sections | ❌ لا يوجد |

### بعد الحل:
| العملية | السلوك |
|---------|--------|
| تصحيح في Table | ✅ Stats تتحدث |
| تصحيح في Candidates | ✅ Stats تتحدث |
| Sync بين sections | ✅ متزامن |

---

## ⚠️ المشكلة المتبقية

### اختلاف الأصناف بين الـ sections

**السبب:** مصدران مختلفان بالتصميم
- CSV = كل manual review items
- JSONL = items لها candidates فقط

**الحل المستقبلي (اختياري):**
1. دمج المصادر
2. عرض تحذير للمستخدم
3. إضافة indicator "has candidates"

**الأولوية:** متوسطة

---

**المطور:** Kiro AI  
**التاريخ:** 2026-06-23  
**الحالة:** ✅ Stats sync مطبق
