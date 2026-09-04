# 04 — Offering stores per item: ايه اللي بيظهر وازاي

## المكان في الـ UI

`src/ui/views/run_db/streamlit_run_tables.py:51-114`:

```python
def render_item_stores_expander(items: list[dict[str, Any]], run_key: str) -> None:
    ...
    st.markdown("**Offering stores per item**")
    for item in unique_items:
        snapshot_rows = fetch_item_stores(run_key, item["item_key"])
        ...
        label = f"{item_name} — {store_count} store(s)"
        with st.expander(label):
            _render_store_table(run_key, item["item_key"])
```

كل صنف من اللي اتطلب بياخد expander فيه table. الـ table فيها كل المخازن اللي عرضت الصنف ده في الـ run الحالي (مش بس الـ winner).

## الـ data source

`fetch_item_stores(run_key, item_key)` في `src/core/database/order_runs_read.py` بتجيب الـ rows من جدول `run_item_stores` في SQLite. الـ schema (من `docs/order_runs_sqlite/02_data_model.md`):

```sql
CREATE TABLE run_item_stores (
    run_key            TEXT,
    item_key           TEXT,
    store_key          TEXT,
    store_product_id   TEXT,
    store_name         TEXT,
    source             TEXT,         -- "tawreed" | "excel-target" | "excel_target"
    public_price       REAL,         -- retailPrice — سعر الجمهور
    purchase_price     REAL,         -- salePrice   — ما تدفعه أنت فعلاً
    discount_percent   REAL,
    available_quantity INTEGER,
    is_winner          INTEGER,      -- 0/1 flag
    ...
);
```

يعني كل صف = "صيدلية/مخزن عرض الصنف ده بسعر معيّن في الـ run ده". الـ `is_winner=1` على الصف اللي اختاره الـ reconciler كأقل `purchase_price` (مع tie-break بالخصم).

## المنطق اللي بيخصّص الـ store_count للـ expander label

في `streamlit_run_tables.py:77-84`:

```python
snapshot_rows = fetch_item_stores(run_key, item["item_key"])
store_count = len(snapshot_rows) if snapshot_rows else 0
if store_count == 0 and item.get("stores_offering"):
    # Fall back to the per-source count when the snapshot was pruned
    store_count = int(item["stores_offering"])
```

- الـ snapshot هو الـ source of truth (الصفوف الفعلي في `run_item_stores`).
- لو مفيش snapshot (مثلاً run قديم قبل ما الخاصية تتفعّل) → fallback على `run_items.stores_offering` (اللي هو per-source count).
- الـ dedup: `seen: set[str]` بيمنع إن الصنف يظهر مرتين لو جاي من Tawreed و Excel target معاً (الـ items list ممكن يكون فيها نفس الـ `item_key` مرتين — واحد per source).

## الـ columns اللي في الجدول

`_render_store_table()` بتعمل:

```python
frame = pd.DataFrame(stores)
frame["is_winner"] = frame["is_winner"].map(_check_mark)
if "source" in frame.columns:
    frame["source"] = frame["source"].map(
        lambda value: STORE_SOURCE_LABELS.get(value, value) if value else "—"
    )
st.dataframe(frame, ...)
```

- `is_winner` → ✅ أو —.
- `source` → 👤 Tawreed أو 📊 Excel target.
- باقي الأعمدة بتظهر كما هي من SQLite (الاسم، السعرين، الخصم، الكمية).

## الـ WIN في الميزة دي

- **مفيد للـ transparency**: الـ user بيشوف كل الخيارات، مش بس الـ winner. لو الـ winner اتغيّر سعره أو مش متاح، يقدر يبص على البديل بسهولة.
- **dedup متعدد المصادر**: لو نفس الصنف جه من Tawreed ومن Excel target، الـ expander واحد بيشوف الاتنين.

## الـ GAP / مشاكل محتاجة تتحل

1. **`purchase_price` NULL لـ Excel target rows** → الجدول بيبان فيه سعر ناقص وده بيحير الـ user. الحل: إما نعالج الـ loader (شوف `03_public_vs_purchase_price.md`) وإما نعرض الـ tooltip "(no purchase price recorded — only public price known)".
2. **`store_key` ممكن يكون فاضي لـ Excel target rows** → لأن الـ loader مش بيولّد warehouse identity (مفيش store_id). في `cli_order_excel_target.py:456-461` مكتوب صراحةً: "the warehouse identity is left empty". ده معناه إن الـ user مش هيقدر يميّز بين مخزنين مختلفين بنفس الـ Excel target key.
3. **الـ sort ما بيظهرش بشكل صريح** → الجدول بيعرض الـ rows بالترتيب اللي رجعتها الـ SQL query. لو مش مرتّبة (store_name مثلاً أو price) ممكن يصعب المقارنة. اقتراح: sort بـ `purchase_price ASC NULLS LAST` والـ winner فوق.
4. **`source` label مش متّسق** → في الـ schema بيبقى `"excel_target"` أو `"excel-target"` أو `"excel-target "`. الـ labels dict بيغطي الـ variants بس ده leaky abstraction.

## الـ schema decisions المهمة من الـ audit

من `docs/order_runs_sqlite/06_implementation_plan.md:264` و `02_data_model.md`:

- ✅ كل offering store بيتسجل (مش بس الـ winner).
- ✅ `is_winner` flag بيتسجل على الـ row الرابح.
- ⚠️ الـ semantic بتاع `salePrice` vs `purchase_price` مربك — `07_risks_and_decisions.md` بيناقش الـ naming convention والـ confusion اللي سببوه.