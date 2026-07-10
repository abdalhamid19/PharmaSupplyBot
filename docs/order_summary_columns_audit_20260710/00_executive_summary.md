# Order Summary Columns Audit - Executive Summary

## Scope

This audit covers the `order_item_summary` CSV/XLSX column problem reported for:

- `winner_sales_price`
- `selected_discount_percent`
- `selected_store_name`
- duplicated `winner_store_name`
- duplicated `winner_discount`
- multi-store values staying packed in one XLSX cell
- quantity being embedded as `(qty N)` inside store/discount text

The requested business meaning is:

- `winner_sales_price` means the actual purchase price.
- `selected_discount_percent` is the same business value as the old `winner_discount`.
- `selected_store_name` is the same business value as the old `winner_store_name`.
- Therefore `winner_store_name` and `winner_discount` must be removed from new summaries.
- When multiple stores are selected, each store, discount, and quantity must have its own columns.

## Main Finding

The root cause was not the XLSX writer itself. The real problem was the row dictionary produced before CSV/XLSX writing.

The old row builder emitted both old names and new names:

- `winner_store_name`
- `winner_discount`
- `selected_store_name`
- `selected_discount_percent`

For CSV, this appeared as visible duplicated columns because CSV headers are rebuilt as a union of all row keys.

For XLSX, the last observed workbook already had fewer duplicate columns in some runs, but multi-store values were still packed into one text value because `order_result_summary` did not use the same splitting logic as `order_item_summary`.

## Implemented Fix

The fix is intentionally small and surgical:

- Removed `winner_store_name` from new `order_item_summary` rows.
- Removed `winner_discount` from new `order_item_summary` rows.
- Kept `selected_store_name` as the canonical store column.
- Kept `selected_discount_percent` as the canonical discount column.
- Added `winner_sales_price` as the actual purchase/sale price from Tawreed payload `salePrice` or `salesPrice`.
- Kept existing `winner_sale_price` unchanged as the public/reference price from `retailPrice`, `publicPrice`, `price`, or `sellingPrice` to avoid breaking existing consumers that may read that column.
- Added shared split logic so both order summary paths can split multi-store values consistently.
- Moved `(qty N)` out of the split store/discount cells into `selected_qty_N` columns.

## New Multi-Store Output Shape

For an input like:

```text
selected_store_name = Warehouse 20 (qty 5) | Warehouse 30 (qty 10)
selected_discount_percent = 20% (qty 5) | 30% (qty 10)
```

The row keeps the original aggregate columns:

- `selected_store_name`
- `selected_discount_percent`

And adds ranked split columns sorted from highest discount to lowest:

- `selected_store_name_1 = Warehouse 30`
- `selected_discount_percent_1 = 30%`
- `selected_qty_1 = 10`
- `selected_store_name_2 = Warehouse 20`
- `selected_discount_percent_2 = 20%`
- `selected_qty_2 = 5`

## Files Changed

- `src/core/ordering/order_selected_fields.py`
- `src/core/ordering/order_winner_fields.py`
- `src/tawreed/matching/tawreed_order_result_summary_rows.py`
- `src/tawreed/matching/tawreed_match_logs.py`
- `tests/core/ordering/test_order_run_artifacts.py`
- `tests/tawreed/matching/test_tawreed_match_logs.py`

## Validation Summary

Commands run:

```powershell
python -m pytest tests/core/ordering/test_order_run_artifacts.py tests/tawreed/matching/test_tawreed_match_logs.py
python tools/run_unit_tests.py
python tools/rule_audit.py
```

Results:

- Focused tests passed: `18 passed`.
- Full unit suite passed: `468 tests passed, 20 skipped`.
- `tools/rule_audit.py` still reports existing baseline violations in the repository. The output includes long-standing file/function/line-length debt across many files, not a test failure from the changed behavior.

## Live MELO Check

A temporary Excel file was created outside the repository at:

```text
C:\Users\USER\AppData\Local\Temp\opencode\melo_order_ar.xlsx
```

It contained:

- code: `87160`
- item: `MELO OINT. 30 GM`
- quantity: `15`

The safe live command was:

```powershell
python run.py order --profile wardany --excel "C:\Users\USER\AppData\Local\Temp\opencode\melo_order_ar.xlsx" --limit 1 --match-only --fast-search --execution-mode auto --prevented-items-excel "C:\Users\USER\AppData\Local\Temp\opencode\missing_prevented.xlsx"
```

Output run:

```text
artifacts/order/wardany/20260710_1957
```

The live output confirmed:

- no `winner_store_name` column in the new CSV/XLSX header
- no `winner_discount` column in the new CSV/XLSX header
- `winner_sales_price` exists and was populated with `52.0`
- `selected_store_name` exists
- `selected_discount_percent` exists

Important note: the live `match-only` path loads match-only Excel rows without using the quantity column, so the live artifact showed `item_qty = 1`. The quantity-15 requirement is covered by the focused unit test that exercises the actual summary row builder with `MELO OINT. 30 GM` and `item_qty = 15`, without mutating the cart.
