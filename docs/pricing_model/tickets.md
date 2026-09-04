# Pricing Model — Implementation Tickets

Four tickets, each independently shippable. Each has: **Goal**, **Files**,
**Acceptance**, **Tests**. Numbered in execution order.

---

## T1. Build the single resolver seam

### Goal
One function (`resolve_store_prices`) returns a `ResolvedPrices` dataclass
for any candidate dict, regardless of source. This becomes the only place in
the codebase that decides what `public_price` / `purchase_price` mean.

### Files
- **New** `src/core/pricing/__init__.py`
- **New** `src/core/pricing/store_price_resolution.py`
- **New** `src/core/pricing/store_price_resolution_provenance.py`

### Design recap
```python
@dataclass(frozen=True)
class ResolvedPrices:
    public_price: float | None
    purchase_price: float | None
    discount_percent: float
    net_price: float | None
    price_provenance: Literal[
        "tawreed_both",
        "tawreed_public_only",
        "tawreed_purchase_only",
        "excel_public_implies_purchase",
        "excel_purchase_implies_public",
        "unknown",
    ]
```

`source_kind` parameter chooses the derivation policy. Discount comes from
`discount_value_as_percent(first_discount_value(store))`. Net = either
`purchase_price` or `public_price` × `(1 − d/100)`, with NULL if both are
NULL.

### Acceptance
- Function exists, is importable as `from src.core.pricing import resolve_store_prices`.
- Old `store_price_fields` still callable (back-compat shim).
- No regression in existing tests.

### Tests
- `tests/core/pricing/test_store_price_resolution.py`:
  - Tawreed both → preserved.
  - Tawreed public only → purchase stays NULL; provenance `"tawreed_public_only"`.
  - Tawreed purchase only → public stays NULL; provenance `"tawreed_purchase_only"`.
  - Excel `public_with_discount` → both set; provenance `"excel_public_implies_purchase"`.
  - Excel `purchase_only` → both set; provenance `"excel_purchase_implies_public"`.
  - Missing discount → net = purchase (no zero division).
  - Discount > 100 % or negative → still returns a non-NaN result.
  - Empty dict → all None, provenance `"unknown"`, net None.

---

## T2. Wire resolver into DB write path + CSV artifact

### Goal
Every `run_item_stores` row carries `public_price` AND `purchase_price` (for
Excel-target rows, the second one is derived). The CSV artifact gains a
`winner_net_price` column.

### Files
- `src/core/database/order_runs_store_values.py` — keep `store_price_fields`
  as a shim that calls the resolver and projects the four flat fields.
- `src/core/database/order_runs_stores.py` — call resolver at row build time.
- `src/core/ordering/order_winner_fields.py` — add `winner_net_price` to the
  artifact dict.
- `src/core/excel_target/excel_target_loader.py` — accept and carry the new
  `price_meaning` field on `TargetProduct`, default `"public_with_discount"`.
- `src/core/config/config_models.py` + `config_factory.py` — add
  `price_meaning: Literal[...] = "public_with_discount"` and optional
  `public_price_col` / `purchase_price_col` to `ExcelTargetConfig`.

### Acceptance
- Excel-target row inserted via the regular run path has both `public_price`
  and `purchase_price` non-NULL (when the source row has a non-empty "سعر").
- Net price in artifact CSV equals `purchase_price × (1 − d/100)` rounded to 2dp.
- Backward-compat: `store_price_fields(store)` still returns the three legacy
  keys (`public_price`, `purchase_price`, `discount_percent`, `currency`).

### Tests
- Update `tests/core/database/test_order_runs_store_values.py`.
- Add `tests/core/excel_target/test_excel_target_loader.py::test_price_meaning_default`.
- Add end-to-end `tests/core/database/test_order_runs_excel_target_e2e.py`:
  build a one-row catalog, run through the matcher, persist to temp DB,
  `fetch_item_stores`, assert both prices + net.

---

## T3. UI: honest display in "Offering stores per item"

### Goal
The user always sees both prices and the net price, and understands why
Excel-target rows show two identical numbers.

### Files
- `src/ui/views/run_db/streamlit_run_tables.py`

### Acceptance
- A `st.caption` sits directly under `**Offering stores per item**` with the
  four-line tooltip text from plan §3.3.
- A second conditional `st.caption` appears when any snapshot row in the run
  has `price_provenance` starting with `"excel_"` (Excel-target rows).
- The per-item expander dataframe shows:
  - All existing columns.
  - A new column **`Net price`** = purchase_price × (1 − d/100), formatted
    `"{:.2f}"`.
  - A new column **`Margin %`** only when both prices are present and
    provenance is not Excel-derived. (Hint, not a UI choice.)
  - A new column **`Provenance`** showing a one-line badge per provenance
    (e.g. "👤 Tawreed", "📊 Excel (public)", "—").
- No layout regressions: dataframe still uses `use_container_width=True`,
  `hide_index=True`.

### Tests
- Add `tests/ui/views/run_db/test_streamlit_run_tables.py` using
  `streamlit.testing.v1.AppTest`. Mock `fetch_item_stores` with three rows
  (Tawreed-both, Tawreed-public-only, Excel-public-implies-purchase), assert
  the captions and the derived columns render.

---

## T4. `--sort-by-net` CLI flag (opt-in)

### Goal
Operators who want to rank candidates by the price they actually pay
(purchase after discount) can flip a flag. Default behaviour unchanged.

### Files
- `src/core/config/config_models.py` — add `sort_by_net: bool = False` to
  `WarehouseStrategyConfig`.
- `src/core/config/config_factory.py` — read `sort_by_net`.
- `src/cli/commands/cli_order.py` — add `--sort-by-net` flag, plumb through
  to the picker; when set, the comparator uses `net_price` first, then falls
  back to current `purchase_price` tie-break.
- `config.example.yaml` — add the new field under `warehouse_strategy:`.

### Acceptance
- `--sort-by-net` is the documented flag; shows up in `--help`.
- Without it, no behaviour change (existing test suite still passes).
- With it, two candidates with different `net_price` order by net first;
  equal net → existing tie-break.

### Tests
- `tests/cli/commands/test_cli_order.py`:
  - `test_sort_by_net_flag_changes_winner`.
  - `test_default_behaviour_unchanged`.
  - Snapshot of comparator: same input, flag off vs on.

---

## Cross-cutting Notes

- **No DB schema change** in any ticket. The resolver is run at write-time.
- **No changes to `v_run_winners` view.** Out of scope per plan §6.
- **Backward compatibility**: every ticket keeps the existing function
  signatures working as shims so other call-sites compile and pass.
- **Order of execution**: T1 → T2 → T3 → T4.
- **Skills used**: codebase-design (deep-module seam), developing-with-streamlit (UI ticket only).

## Verification Checklist (run after each ticket)

```
.venv\Scripts\python.exe -m pytest tests/core/pricing tests/core/database tests/core/excel_target -q
.venv\Scripts\python.exe -m pytest tests/cli -q
.venv\Scripts\python.exe -m pytest tests/ui -q
```

(Adjust to project's actual pytest entry point.)