# PharmaSupplyBot Project Map

## [TECH_STACK]

- Python 3.12.3 runtime in `.venv`.
- Playwright 1.59.0 for Tawreed browser/session and API-backed automation.
- pandas 3.0.2 and openpyxl 3.1.5 for spreadsheet input/output.
- PyYAML 6.0.3, python-dotenv 1.2.2, and Streamlit 1.57.0 for config and UI.

## [SYSTEM_FLOW]

- `run.py export-products` loads config, selects authenticated profiles, and opens
  a saved Tawreed session.
- The export flow prepares the order/products page, captures Tawreed
  `product-search` request metadata, fetches product pages, normalizes rows, and
  writes CSV, XLSX, and TXT artifacts under the profile output directory.
- Target export order: general catalog pages, English alphabet searches, Arabic
  alphabet searches, then final deduplication before files are written.

## [ARCHITECTURE]

- CLI parsing and profile dispatch stay in `src/cli`.
- Browser/session lifecycle stays in `src/tawreed/tawreed_product_export_flow.py`.
- Product-search API pagination stays in `src/tawreed/tawreed_product_export_api.py`.
- Ordered general/English/Arabic export search terms and captured search request
  iteration stay in `src/tawreed/tawreed_product_export_searches.py`.
- Row normalization stays in `src/tawreed/tawreed_product_export_rows.py`.
- Product identity and deduplication stay in
  `src/tawreed/product_export_deduplicator.py`.

## [ORPHANS & PENDING]

- Pending: capture actual search request payloads for each export query.
- Done: define general, English, and Arabic export search terms in required order.
- Done: fetch all API pages for each captured search request in input order.
- Pending: apply final deduplication before row normalization and output writing.
- Pending: apply `--limit` to the total final unique products.
- Pending: verify `sale_price` values in CSV, XLSX, and TXT outputs.
