# Solution Plan And Validation

## Solution Options Considered

### Option 1: Rename Old Columns In Place

This would keep `winner_store_name` and `winner_discount` internally and rename them only at CSV/XLSX write time.

Rejected because it hides the duplicate semantics and makes CSV/XLSX behavior depend on writer-specific filtering.

### Option 2: Remove The Old Columns At The Row Source

This is the chosen solution.

It removes the duplicate columns where they are created and keeps the artifact writer generic.

Benefits:

- CSV and XLSX receive the same clean row keys.
- No writer-specific special cases.
- The fix is close to the bug.
- The rest of the order logic remains unchanged.

### Option 3: Change Store Selection To Store Structured Lists

This would be more architecturally pure, because the bot would preserve selected stores as structured data instead of a joined string.

Rejected for this change because it would touch more of the Tawreed runtime flow and increase regression risk. The current request can be solved safely at the artifact-row boundary.

### Option 4: Delete `winner_sale_price` Too

Rejected because the user only requested removing `winner_store_name` and `winner_discount`. Existing consumers may depend on `winner_sale_price` as the public/reference price column.

The new `winner_sales_price` was added for purchase price while preserving `winner_sale_price` for compatibility.

## Implemented Design

### Shared Split Helper

Added:

```text
src/core/ordering/order_selected_fields.py
```

Responsibilities:

- Keep canonical aggregate columns:
  `selected_store_name`, `selected_discount_percent`
- Split multi-store text on `|`.
- Extract `(qty N)` into separate `selected_qty_N` columns.
- Sort split pairs from highest discount to lowest.

### Order Item Summary Row

Changed:

```text
src/core/ordering/order_winner_fields.py
```

New behavior:

- emits `winner_sales_price`
- no longer emits `winner_store_name`
- no longer emits `winner_discount`
- emits canonical selected fields and split columns via the shared helper

### Order Result Summary Row

Added:

```text
src/tawreed/matching/tawreed_order_result_summary_rows.py
```

Changed:

```text
src/tawreed/matching/tawreed_match_logs.py
```

New behavior:

- `order_result_summary` uses the same split selected-store logic.
- `tawreed_match_logs.py` stays focused on appending artifacts.

## Tests Added

### `test_winner_sales_price_and_split_selected_stores`

File:

```text
tests/core/ordering/test_order_run_artifacts.py
```

This verifies:

- `winner_sales_price` comes from `salePrice`.
- `winner_sale_price` remains the public/reference price.
- `winner_store_name` is absent.
- `winner_discount` is absent.
- split columns are sorted by discount descending.
- `(qty N)` is moved into `selected_qty_N`.

### `test_melo_multi_store_summary_shape`

File:

```text
tests/core/ordering/test_order_run_artifacts.py
```

This verifies the requested item shape directly:

- item name: `MELO OINT. 30 GM`
- quantity: `15`
- `winner_sales_price` is populated
- selected stores split correctly
- selected discounts split correctly
- quantities split into their own columns

### `test_order_result_summary_splits_selected_stores_and_quantities`

File:

```text
tests/tawreed/matching/test_tawreed_match_logs.py
```

This verifies the second artifact path, so the XLSX/CSV behavior does not diverge between `order_item_summary` and `order_result_summary`.

## Live Validation On MELO

The safe live check used `--match-only`, so it did not add the item to the cart.

Command:

```powershell
python run.py order --profile wardany --excel "C:\Users\USER\AppData\Local\Temp\opencode\melo_order_ar.xlsx" --limit 1 --match-only --fast-search --execution-mode auto --prevented-items-excel "C:\Users\USER\AppData\Local\Temp\opencode\missing_prevented.xlsx"
```

Run output:

```text
artifacts/order/wardany/20260710_1957
```

Observed `order_item_summary_20260710_1957.csv` headers included:

- `winner_sales_price`
- `selected_store_name`
- `selected_discount_percent`

Observed headers did not include:

- `winner_store_name`
- `winner_discount`

Observed MELO row contained:

- `item_name = MELO OINT. 30 GM`
- `winner_sale_price = 80.0`
- `winner_sales_price = 52.0`
- `selected_store_name = شركه الهدي - ريان سابقا (الجيزه)`
- `selected_discount_percent = 35%`

Important: the live `match-only` loader intentionally loads match-only rows as code/name catalog rows and does not use the quantity column. That is why the live row showed `item_qty = 1`. The quantity-15 behavior is verified by unit test without mutating cart state.

## Validation Commands And Results

Focused tests:

```powershell
python -m pytest tests/core/ordering/test_order_run_artifacts.py tests/tawreed/matching/test_tawreed_match_logs.py
```

Result:

```text
18 passed
```

Full test suite:

```powershell
python tools/run_unit_tests.py
```

Result:

```text
468 tests passed, 20 skipped
```

Rule audit:

```powershell
python tools/rule_audit.py
```

Result:

```text
rule_audit_violations
```

The audit still reports existing repository baseline debt. This project already has many file-length, function-length, and line-length violations recorded across unrelated modules. The behavioral tests passed.

## Commit Plan

Stage only the intended source, test, and report files:

- `src/core/ordering/order_selected_fields.py`
- `src/core/ordering/order_winner_fields.py`
- `src/tawreed/matching/tawreed_order_result_summary_rows.py`
- `src/tawreed/matching/tawreed_match_logs.py`
- `tests/core/ordering/test_order_run_artifacts.py`
- `tests/tawreed/matching/test_tawreed_match_logs.py`
- `docs/order_summary_columns_audit_20260710/*.md`

Do not stage `state/wardany.json`, because the live Tawreed session refresh changed tokens during validation and session state must not be committed.
