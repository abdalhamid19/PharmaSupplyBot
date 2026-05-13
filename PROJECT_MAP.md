# PharmaSupplyBot Project Map

## [TECH_STACK]

- Python 3.12.3 runtime in `.venv`.
- Playwright 1.59.0 for Tawreed browser/session automation.
- pandas 3.0.2 and openpyxl 3.1.5 for spreadsheet input/output.
- rapidfuzz 3.14.5 for component-aware drug matching and indexed fuzzy search.
- aiohttp 3.13.5 for optional async AI verification/search/review calls.
- PyYAML 6.0.3, python-dotenv 1.2.2, and Streamlit 1.57.0 for config and UI.

## [SYSTEM_FLOW]

- `run.py order` keeps the live Tawreed search flow: it searches Tawreed per item,
  evaluates candidates through `src/core/product_matching.py`, and writes order or
  match-only summaries under `artifacts/<profile>/`.
- `run.py export-products` exports Tawreed catalog rows into
  `artifacts/<profile>/tawreed_products.csv|xlsx|txt`.
- `run.py match-products` matches an inventory Excel/CSV against an exported
  Tawreed CSV. `--profile wardany` resolves to
  `artifacts/wardany/tawreed_products.csv`; `--tawreed-csv` overrides it.
- Standalone product matching runs algorithmic matching first, then optional AI
  verification, AI search, and AI review when API keys are configured.
- Streamlit exposes the same product matching command in the `Product Matching`
  tab and runs it through the existing isolated subprocess runner.

## [ARCHITECTURE]

- CLI parsing and command dispatch stay in `src/cli`.
- Streamlit presentation and subprocess orchestration stay in `src/ui`.
- Tawreed browser automation stays in `src/tawreed`.
- Shared live-search scoring stays in `src/core/product_matching.py`.
- Component parsing, indexed CSV matching, AI verification/search/review, model
  rotation, and detailed trace logging stay in `src/core/drug_matching`.
- Shared candidate-level trace rows and async logging setup stay in
  `src/core/matching_trace.py`.

## [ORPHANS & PENDING]

- None.

## [VALIDATION]

- `.venv/bin/python -m unittest discover -s tests -q`: 214 passed.
- `.venv/bin/python tools/rule_audit.py`: rule_audit_ok.
- Smoke run succeeded:
  `.venv/bin/python run.py match-products --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 5 --no-ai --trace --output artifacts/wardany/match_products_smoke.csv`.
- AI-disabled smoke run succeeded without API keys and logged AI skip reasons:
  `.venv/bin/python run.py match-products --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 1 --output artifacts/wardany/match_products_ai_smoke.csv`.
- CLI help checks succeeded for `run.py`, `order`, `match-products`, and
  `export-products`.
- Streamlit started locally on `http://127.0.0.1:8502` and returned HTTP 200.
- Safe live smoke succeeded without changing the cart:
  `.venv/bin/python run.py order --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 1 --match-only --fast-search`.
