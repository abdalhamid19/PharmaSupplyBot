# Pricing Model for Excel Target — Plan

## 0. Background / Context

The project matches pharmacy needs (from Excel stock-out files) against two surfaces:

1. **Tawreed (API)** — full price pairs: `publicPrice`/`retailPrice` (retail) + `salePrice` (pharmacy).
2. **Excel target** — a vendor pricelist (one column `سعر`, one column `الخصم`).

Both surfaces feed the same matching engine and the same DB (`run_item_stores`).

In the DB, every snapshot row carries two price columns:

- `public_price` — what the **end customer** pays.
- `purchase_price` — what the **pharmacy pays the warehouse**.

Today's behaviour:

| Source       | `public_price` (DB)         | `purchase_price` (DB)         | `discount_percent` |
|--------------|-----------------------------|-------------------------------|--------------------|
| Tawreed API  | `retailPrice` / `publicPrice` / `price` / `sellingPrice` | `salePrice` / `salesPrice` | parsed via `tawreed_pricing.first_discount_value` |
| Excel target | **always NULL** ❌ | the column "سعر" (placed under `salePrice` in candidate dict) | parsed from column "الخصم" |

The column "سعر" in an Excel target is the **public retail price**. There is no
purchase-price column in the file. The pharmacy's purchase price is therefore
**derivable**: `purchase_price = public_price × (1 − discount_percent / 100)`.

This is currently **not** computed anywhere; only Tawreed rows expose a true
purchase price. The result is misleading "Offering stores per item" tables
where Excel-target rows show NULL on one side and a single price on the other.

## 1. Goal

1. Make every snapshot row honest: a row should either carry both `public_price`
   and `purchase_price`, or carry one explicit price **with a clear label** in
   the UI explaining which one is present and which is derived.
2. Compute the **net (cassirol) price** as a first-class value the strategy can
   sort on and the user can read.
3. Add a config flag per Excel target so operators can opt-in to a different
   interpretation if their Excel file means something else.
4. Touch no DB schema; compute the derived columns at write-time so legacy
   runs still work.

## 2. Out of Scope

- No DB migration; no new columns. (Why: matches are computed in Python anyway,
  and a migration would force a re-run of every historical run.)
- No new Tawreed fields.
- No change to `run_item_stores` schema.

## 3. Design

### 3.1. One seam for "what does this row mean"

A new module `src/core/pricing/store_price_resolution.py` owns the rule
"given a candidate dict, return the four normalised values":

- `public_price: float | None`
- `purchase_price: float | None`
- `discount_percent: float`
- `net_price: float | None` (= the value the pharmacy effectively pays)

The module is a deep function with one entry point:

```python
def resolve_store_prices(store: dict, *, source_kind: str) -> ResolvedPrices: ...
```

where `source_kind` is one of `"tawreed" | "excel_target"`. The function:

1. Reads `public_price` from the keys in `PUBLIC_PRICE_KEYS` (current tuple).
2. Reads `purchase_price` from the keys in `PURCHASE_PRICE_KEYS`.
3. Reads `discount_percent` via the existing `discount_value_as_percent` helper.
4. **If only one of public/purchase is present**:
   - For Tawreed rows: keep NULLs as-is (the API genuinely lacks them).
   - For Excel rows: copy the single price to **both** columns **and** record
     the derivation rule in a `price_provenance` field (a `Literal` string).
5. Computes `net_price = purchase_price × (1 − discount/100)` when
   `purchase_price` and `discount_percent` are present, else
   `public_price × (1 − discount/100)`.

Returned dataclass:

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

This module **replaces** the current `store_price_fields` (and the two-key
fallback lists stay where they are, just consumed by the resolver). The single
resolver is now the one seam tests must cover.

### 3.2. Excel target: explicit price meaning per file

Two settings on `ExcelTargetConfig` (`src/core/config/config_models.py`):

- `price_meaning: Literal["public_with_discount", "purchase_only", "public_only"]`
  - default: `"public_with_discount"` (matches today's actual usage).
- Optional `public_price_col` / `purchase_price_col` for the rare vendor that
  sends both columns. Same shape as the existing `price_col`/`discount_col`.

`price_meaning` is threaded through `excel_target_loader.TargetProduct` so the
candidate dict can carry a new field `priceMeaning: str`. The resolver reads
this field and chooses the derivation rule in 3.1.

### 3.3. UI: surface the model honestly

Two changes, both in `src/ui/views/run_db/streamlit_run_tables.py`:

1. **In `_render_store_table`**, after the dataframe render, compute
   `net_price` in Python for each row and add three derived columns:
   - `Net price (purchase after discount)`
   - `Margin hint` (Tawreed rows only)
   - `Provenance` (badge "📊 price-as-public" / "👤 Tawreed" / "—" ).
2. **Add a header tooltip** above "Offering stores per item":
   `st.caption(...)` explaining what the two prices mean and how net price
   is derived. Wording:

   > 💡 **Public** = price the warehouse charges end customers.
   > **Purchase** = price the pharmacy actually pays.
   > **Net** = purchase after the discount.
   > For Excel targets the file lists only the public price; the purchase
   > price is derived as `public × (1 − discount%)`.

A second, optional caption that appears only when the run contains at least
one Excel-target row:

   > 📊 This run includes Excel-target stores. Their public and purchase
   > prices are identical by definition — only the net price (after
   > discount) and the discount % vary.

### 3.4. Strategy: sort by net when requested

`cli_order.py` (and any other picker) currently uses `purchase_price` only
when it is non-NULL. After this change `purchase_price` is **always** set for
Excel-target rows, so the existing tie-break will start including them. Add
an opt-in `sort_by_net: bool = False` flag on `warehouse_strategy` (config):

- `False` (default) keeps today's behaviour so existing runs don't change.
- `True` sorts by `net_price` (computed by the resolver) before any other
  tie-break. Falls back gracefully when `net_price` is missing for a row.

CLI flag: `--sort-by-net` to flip it on.

### 3.5. Tests

- New unit tests for the resolver (`tests/core/pricing/test_store_price_resolution.py`):
  - Tawreed row with both prices → both preserved, net computed.
  - Tawreed row missing one → that one stays NULL, no derivation.
  - Excel row with `price_meaning="public_with_discount"` → both set,
    provenance `"excel_public_implies_purchase"`.
  - Excel row with `price_meaning="purchase_only"` → both set,
    provenance `"excel_purchase_implies_public"`.
  - Missing discount → net falls back to purchase (no division by zero).
- Update `tests/core/database/test_order_runs_store_values.py` to use the
  resolver and assert the new behaviour.
- Update `tests/cli/commands/test_cli_order.py` for the new
  `--sort-by-net` flag and the net-based tie-break.
- One end-to-end test: load an Excel target, run one item through
  `match_item_against_all_targets`, write to a temp DB, query `fetch_item_stores`,
  assert both prices and net price are present and non-NULL.

## 4. Files Touched

| File | Change |
|---|---|
| `src/core/pricing/__init__.py` | New module. |
| `src/core/pricing/store_price_resolution.py` | New — the single resolver. |
| `src/core/pricing/store_price_resolution_provenance.py` | New — `Literal` + helpers. |
| `src/core/config/config_models.py` | Add `price_meaning`, optional price columns to `ExcelTargetConfig`; add `sort_by_net` to `warehouse_strategy`. |
| `src/core/config/config_factory.py` | Read new fields with safe defaults. |
| `src/core/excel_target/excel_target_loader.py` | Carry `priceMeaning` into candidate dict. |
| `src/core/database/order_runs_store_values.py` | Re-export `resolve_store_prices`; keep backward-compat shim for `store_price_fields`. |
| `src/core/database/order_runs_stores.py` | Use the resolver at row-build time. |
| `src/core/ordering/order_winner_fields.py` | Compute `winner_net_price` field for the artifact CSV; reuse resolver. |
| `src/cli/commands/cli_order.py` | Read `--sort-by-net`; honour `sort_by_net` in tie-break. |
| `src/ui/views/run_db/streamlit_run_tables.py` | Add derived columns + tooltip + caption. |
| `docs/pricing_model/plan.md` | This file. |
| `tests/core/pricing/test_store_price_resolution.py` | New. |
| `tests/core/database/test_order_runs_store_values.py` | Update to resolver-based behaviour. |
| `tests/cli/commands/test_cli_order.py` | Net tie-break tests. |
| `tests/core/excel_target/test_excel_target_loader.py` | `priceMeaning` carry-over. |

## 5. Rollout

1. Land the resolver + tests. (No behaviour change.)
2. Land the loader/DB write-path + tests. (Excel-target rows start carrying
   both prices; CSV artifacts gain a `winner_net_price` column.)
3. Land the UI tooltip/derived columns. (User-visible.)
4. Land the `--sort-by-net` CLI flag behind default-off. (Optional opt-in.)

Each step is independently testable and reverts cleanly.

## 6. Open Questions

- Should we also add `winner_net_price` to the `v_run_winners` view?
  Pro: one query for analysts. Con: requires a schema bump on the view.
  Decision: **out of scope**, revisit after step 3 if users ask.
- Should `price_provenance` land in the DB or stay a runtime-only field?
  Decision: **runtime only** for now; revisit when we want an audit trail.