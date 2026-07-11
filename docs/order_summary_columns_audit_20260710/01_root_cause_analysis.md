# Root Cause Analysis

## What Was Observed

The existing local artifact `artifacts/wardany/order_item_summary.csv` had both canonical and duplicate winner columns in its header:

- `winner_store_name`
- `winner_discount`
- `selected_store_name`
- `selected_discount_percent`
- `winner_Purchase_Price`

The existing local artifact `artifacts/wardany/order_item_summary.xlsx` already showed a slightly different header shape, but older duplicate columns were still present at the end of that workbook in the inspected file.

The latest completed run inspected before the fix was:

```text
artifacts/order/wardany/20260710_1934
```

Its CSV header still had:

- `winner_store_name`
- `winner_discount`
- `selected_store_name`
- `selected_discount_percent`

That confirmed the duplication was real in generated artifacts, not only a display issue.

## Root Cause

The root cause was in `src/core/ordering/order_winner_fields.py`.

The function `candidate_summary_fields()` produced winner fields using this business mapping:

- `winner_store_name` was filled from the selected store name.
- `winner_discount` was filled from the selected discount percent.

After adding canonical selected fields, the row builder had both old and new field names for the same values.

This created duplicated semantic columns:

- `winner_store_name` duplicated `selected_store_name`.
- `winner_discount` duplicated `selected_discount_percent`.

The CSV writer was behaving correctly. It writes whatever keys are present in the row dictionary. Because both key sets existed, both sets appeared in CSV.

## Why XLSX Looked Different

The XLSX writer also writes row keys, but it rewrites or extends the workbook schema based on existing workbook headers and incoming row keys.

That means two things can happen depending on workbook history:

- A fresh XLSX file reflects the current row keys.
- An older XLSX file can keep old headers if it was generated before a schema cleanup and then later extended.

So the visible behavior can differ between CSV and XLSX even when the row generator is the real source of truth.

## Why Multi-Store Values Stayed Packed

Multi-store selections are stored earlier in the pipeline as a single joined string.

The source helper is `src/tawreed/store/tawreed_store_summary.py`:

```text
Store A (qty 5) | Store B (qty 10)
```

That format is useful for compact logs, but it is not good for spreadsheet analysis.

The initial fix only split the values in the order-item winner field path. Another path, `append_order_result_summary()` in `src/tawreed/matching/tawreed_match_logs.py`, still wrote the aggregate string directly. That explains why one summary could look split while another still had packed cells.

The corrected fix shares one splitter in `src/core/ordering/order_selected_fields.py` and applies it to both paths.

## Possible Causes Considered

### CSV Writer Bug

This was considered because the problem was reported as visible in CSV.

Rejected as the main cause because the CSV writer uses `csv.DictWriter` and writes the exact row keys. It does not invent `winner_store_name` or `winner_discount`.

### XLSX Writer Bug

This was considered because XLSX had packed multi-store cells.

Partially relevant, but not the root cause. The XLSX writer writes row keys correctly. The packed values came from the row data itself being one joined string.

### Historical Workbook Schema

This was considered because existing XLSX workbooks can retain old headers.

Relevant for old files only. A fresh run after the fix produces headers without `winner_store_name` and `winner_discount`.

### Store Selection Logic

This was considered because values are created in `record_selected_stores()`.

Not the main bug. Store selection correctly preserves multi-store choices. The problem was the artifact representation, not the selection decision.

### Naming Confusion Between Sale Price and Sales Price

This was a real requirement issue.

The existing `winner_sale_price` was already used as a public/reference price based on `retailPrice`, `publicPrice`, `price`, or `sellingPrice`.

The requested `winner_Purchase_Price` means purchase price. Tawreed payloads expose that as `salePrice` in the observed data, so the implementation maps:

- `winner_Purchase_Price` from `salePrice` or `salesPrice`
- `winner_sale_price` remains unchanged for compatibility

## Most Likely Root Cause Ranking

1. Highest confidence: duplicate semantic fields were emitted by the row builder.
2. High confidence: multi-store values were packed because joined strings were not split at artifact row creation time.
3. Medium confidence: historical XLSX/CSV files made the symptom look inconsistent across formats.
4. Low confidence: writer-layer issues, because the writers correctly persisted the keys and values they received.

## Why The Fix Avoids Breaking Existing Logic

The fix does not change:

- product matching
- store selection
- discount calculation
- add-to-cart behavior
- AI verification
- manual review behavior
- artifact file path behavior

It only changes the shape of artifact rows after a decision has already been made.

That keeps the business logic intact and limits regression risk.
