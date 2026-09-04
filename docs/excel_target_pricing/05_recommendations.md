# 05 — اقتراحاتي لتحسين الميزة (محدّثة بناءً على إن الـ Excel يحوي retail price)

> **السياق المؤكّد:** الـ Excel Target يحوي **سعر بيع الصيدلية للجمهور (retail)**. الـ loader الحالي **صح في الـ semantic** (بيحط الرقم في `public_price`)، لكن (أ) الـ winner logic بيتجاهل الـ Excel target، و(ب) الـ UI مش بتوضّح للـ user إن ده سعر بيع مش سعر شراء.

الاقتراحات مرتّبة من الأهم للأقل أهمية، وكل واحد فيه: المشكلة، الحل المقترح، الـ impact على الـ pipeline الحالي.

---

## 1) 🔴 فصل الـ Excel target عن الـ winner competition (الأسلم في الـ short term)

### المشكلة
- الـ Excel يحوي retail price (سعر بيع الصيدلية للجمهور).
- الـ Tawreed بيعطي wholesale price (سعر شراء الصيدلية بعد الخصم).
- المقارنة بينهم apples-to-oranges: مين الأرخص للـ صيدلي فعلاً؟ مش واضح.
- الـ winner logic الحالي بيستخدم `purchase_price` فقط، فالـ Excel target rows عمرها ما بتكسب.

### الحل
**أ) في الـ reconcile logic** (`src/cli/commands/cli_order.py:313-328`):

```python
def _is_better(candidate, current):
    """Excel target rows never compete on purchase_price (no apples-to-apples)."""
    cand_src = candidate.get("source")
    curr_src = current.get("source")

    # Excel target participates only when there's no Tawreed alternative
    if cand_src == "excel_target" and curr_src and curr_src != "excel_target":
        return False
    if curr_src == "excel_target" and cand_src and cand_src != "excel_target":
        return True

    # Tawreed-vs-Tawreed: existing logic
    cand_price = candidate.get("purchase_price")
    curr_price = current.get("purchase_price")
    ...
```

**ب) في الـ DB schema** (`run_item_stores.is_winner`):
- الـ Excel target rows دايماً `is_winner = 0` (أو NULL).

**ج) في الـ UI** (`streamlit_run_tables.py`):
- الجدول يبقى فيه sub-header للـ Excel target rows:
  ```
  Offering stores per item
  ├── Tawreed (winner competition)
  └── 📊 Excel target — retail prices (reference only)
  ```
- الـ Excel rows دايماً تحت sub-section منفصل.

### الـ Impact
- ✅ الـ user بيشوف الـ Excel target prices كـ reference من غير confusion.
- ✅ الـ winner logic يبقى apples-to-apples (wholesale vs wholesale).
- ✅ الـ "best deal" للصيدلي يبقى من Tawreed (اللي هو سعر الشراء الفعلي).
- ⚠️ تغيير في الـ winner logic — لازم regression tests.

---

## 2) 🟠 وضّح الـ semantic في الـ UI لكل صف

### المشكلة
- الـ Excel target row بيظهر بـ `public_price = 100` و `purchase_price = NULL` في نفس الجدول.
- الـ user مش فاهم هو سعر بيع ولا شراء.

### الحل
في `_render_store_table` (`streamlit_run_tables.py:101-113`):

```python
def _annotate_prices(frame):
    """Add semantic annotations so users never confuse public vs purchase price."""
    if "source" in frame.columns and "public_price" in frame.columns:
        excel_mask = frame["source"].str.contains("excel", case=False, na=False)
        frame.loc[excel_mask, "price_note"] = "💰 retail (بيع للعميل)"
        frame.loc[~excel_mask, "price_note"] = "💵 purchase (سعر شراء للصيدلية)"
    return frame
```

والـ columns تترتّب:
- Tawreed rows → `purchase_price` (اللي الصيدلي بيدفعه).
- Excel target rows → `public_price` (اللي الصيدلية بتبيع بيه للعميل).

### الـ Impact
- ✅ يقلل الـ confusion بشكل كبير.
- ⚠️ تغيير في الـ display فقط — مفيش breaking.

---

## 3) 🟠 إصلاح التعليق المغلوط في الكود

### المشكلة
في `src/cli/commands/cli_order_excel_target.py:456-461`:

```python
catalogs only carry the pharmacy's purchase price + discount + name, so
the public/retail price is left empty and the warehouse identity is
```

ده **مغلوط** في سياق الـ workflow بتاعنا — الـ Excel يحوي retail price مش purchase price.

### الحل
حدّّث التعليق ليصبح:

```python
The Excel catalog rows carry the pharmacy's retail price (public_price)
plus optional code. They never carry a purchase_price, so they cannot
compete on the wholesale winner race — see _is_better() in cli_order.py.
```

### الـ Impact
- ✅ documentation accuracy.
- ⚠️ comment only، صفر risk.

---

## 4) 🟡 أضف `store_id` / `store_name` صريحين في الـ config

### المشكلة
- الـ `run_item_stores` row للـ Excel target عندها `store_key` و `store_name` فاضيين.
- الـ user مش بيشوف مين المخزن اللي جاي منين.

### الحل
```yaml
excel_targets:
  my_store:
    name: "Excel Target Demo"
    store_id: "excel-store-001"
    store_name: "صيدلية/مخزن المعادي"
    path: "data/input/excel target/sample.xlsx"
    name_col: "اسم الصنف"
    price_col: "السعر"
```

### الـ Impact
- ✅ كل row في "Offering stores per item" يبقى ليه اسم واضح.
- ⚠️ تغيير additive.

---

## 5) 🟡 sort الـ table: winner فوق + purchase_price ASC NULLS LAST

### المشكلة
- الجدول بيظهر rows بترتيب عشوائي.
- الـ user محتاج يقارن بسرعة.

### الحل
في `_render_store_table`:

```python
frame = frame.sort_values(
    by=["is_winner", "source", "purchase_price"],
    ascending=[False, True, True],
    na_position="last",
)
```

ولو طبقنا الاقتراح #1، نخلّي الـ Excel target rows دايماً تحت (separated).

### الـ Impact
- ✅ UX أحسن بكتير.
- ⚠️ pure display change.

---

## 6) 🟢 Future enhancement: دعم العمودين لو الـ Excel يحوي الاتنين

### الحل (لو الـ Excel فيه العمودين)
```yaml
excel_targets:
  my_store:
    name_col: "اسم الصنف"
    public_price_col:   "سعر البيع"      # سعر بيع الصيدلية للجمهور
    purchase_price_col: "سعر الشراء"     # سعر شراء الصيدلية من المخزن
    discount_col: "الخصم"
```

الـ loader يحدّث الـ `TargetProduct`:

```python
@dataclass(frozen=True)
class TargetProduct:
    code: str
    name: str
    public_price:   float | None = None
    purchase_price: float | None = None
    discount_percent: float = 0.0

    def to_candidate_dict(self):
        d = {
            "productNameEn": self.name,
            "discountPercent": self.discount_percent,
            "storeProductId": self.code or ...,
            "excelTarget": True,
        }
        if self.public_price is not None:
            d["publicPrice"] = self.public_price
            d["salePrice"]    = self.public_price
        if self.purchase_price is not None:
            d["purchase_price"] = self.purchase_price
        return d
```

في الحالة دي الـ Excel target ينافس على winner بشكل صحيح (لأن `purchase_price` متاح).

### الـ Impact
- ✅ الـ feature بتفتح لـ scenario جديد.
- ⚠️ breaking change — لازم migration plan.

---

## 7) 🟢 freshness timestamps + stale badge

من الـ core idea: "علامات زمنية لتاريخ آخر تحديث".

### الحل
- سجّل `excel_target_loaded_at` في الـ row metadata.
- اعرض `🕒 Updated 2h ago` في الـ UI جنب اسم المخزن.
- لو `>24h` → badge `⚠️ stale`.

### الـ Impact
- ✅ يطابق الـ value proposition.
- ⚠️ decision: freshness من آخر رفع ولا من آخر تعديل في الملف؟

---

## 8) 🟢 audit logs للـ confusion

### الحل
- سجّل info log في `cli_order.py` لما Excel target row يكون في نفس item مع Tawreed rows — لأن ده الـ interesting case.
- سجّل warning لو الـ Excel target public_price > 5× الـ Tawreed purchase_price (suspect retail).

### الـ Impact
- ✅ debugging tool.
- ⚠️ low-effort.

---

## ترتيب الأولويات اللي بنصح بيه

| # | الاقتراح                                              | الجهد | الأثر |
|---|-------------------------------------------------------|------|------|
| 1 | فصل الـ Excel target عن winner competition            | متوسط | عالي |
| 2 | وضّح الـ semantic في الـ UI (`price_note`)             | منخفض | عالي |
| 3 | إصلاح التعليق المغلوط في الكود                        | منخفض | متوسط |
| 4 | `store_id` / `store_name` صريحين في الـ config          | منخفض | عالي |
| 5 | sort winner فوق                                       | منخفض | متوسط |
| 6 | دعم العمودين (لو الـ Excel يحوي الاتنين) | متوسط | متوسط |
| 7 | freshness timestamps                                  | متوسط | متوسط |
| 8 | audit logs للـ anomalies                              | منخفض | منخفض |

**الـ MVP المقترح:** #1 + #2 + #3 + #4 (حلّ الـ winner logic، وضّح الـ UI، أصلح التعليق، أضف الـ store identity).

ده بيخلّي الـ Excel target feature **مفيدة وآمنة** من غير ما نكسر حاجة في الـ Tawreed pipeline.

---

## ملاحظات على الـ skills اللي استخدمتها

- استخدمت الـ local knowledge في `src/` و `docs/` بشكل أساسي.
- ما حملتش skill من النت لأن الـ task ده تفسيري/توثيقي بحت (مش code execution، مش browser automation، مش Streamlit widget development).
- لو حبّيت بعد كده نعمل code changes، الـ skills اللي هنحتاجها:
  - `developing-with-streamlit` — للـ UI changes (#1, #2, #5).
  - `Pytest Testing` أو `tdd` — للـ reconcile logic (#1) والـ loader (#6).
  - `implementing-feature` — لتنظيم الـ PR.

  لو قررت نتحرك، ابدأ بـ #3 (إصلاح التعليق) عشان يبني momentum مع أقل risk.