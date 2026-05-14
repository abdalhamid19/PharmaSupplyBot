# PharmaSupplyBot Project Map

## [TECH_STACK]

- Python 3.12.3 runtime in `.venv`.
- Playwright 1.59.0 for Tawreed browser/session automation.
- pandas 3.0.2 and openpyxl 3.1.5 for spreadsheet input/output. PyPI latest on
  2026-05-13 is pandas 3.0.3 and openpyxl 3.1.5.
- rapidfuzz 3.14.5 for component-aware drug matching and indexed fuzzy search.
- aiohttp 3.13.5 for optional async AI verification/search/review calls.
- PyYAML 6.0.3, python-dotenv 1.2.2, and Streamlit 1.57.0 for config and UI.

## [SYSTEM_FLOW]

- `run.py order` keeps the live Tawreed search flow: it searches Tawreed per item,
  evaluates candidates through `src/core/product_matching.py`, then can optionally
  run active AI verify/search/review with strict thresholds via `--ai`.
- Order AI is opt-in. Accepted AI decisions can correct/select the active match;
  low-confidence or review-rejected AI decisions are blocked and written to
  `manual_review`.
- Each order run writes `order_item_summary_<run_id>.csv/.txt`,
  `order_ai_trace_<run_id>.csv/.txt`, and `manual_review_<run_id>.csv/.txt`
  when review rows exist.
- Order AI trace rows can mix final, phase-level, and provider-attempt metadata;
  artifact writers keep a union CSV schema so retry/status columns are preserved.
- `run.py export-products` exports Tawreed catalog rows into
  `artifacts/export-products/<profile>/<run_id>/`.
- `run.py match-products` matches an inventory Excel/CSV against an exported
  Tawreed CSV. `--profile wardany` resolves to the newest exported Tawreed
  catalog from the new layout or legacy fallback; `--tawreed-csv` overrides it.
- Standalone product matching runs algorithmic matching first, then optional AI
  verification, AI search, and AI review when API keys are configured.
- Streamlit exposes the same product matching command in the `Product Matching`
  tab and runs it through the existing isolated subprocess runner.
- Streamlit Order exposes the same order AI flags and browses command/profile/run
  artifact folders.
- New command outputs use `artifacts/<command>/<profile>/<run_id>/` with
  timestamped files. Old flat outputs were moved under `artifacts/legacy/...`.

## [ARCHITECTURE]

- CLI parsing and command dispatch stay in `src/cli`.
- Streamlit presentation and subprocess orchestration stay in `src/ui`.
- Tawreed browser automation stays in `src/tawreed`.
- Shared live-search scoring stays in `src/core/product_matching.py`.
- Shared candidate id normalization stays in `src/core/candidate_identity.py` so
  matching, AI, and artifacts agree on orderable Tawreed ids.
- Shared item code/name normalization stays in `src/core/item_text.py` and is
  reused by prevented-items and cart-removal input handling.
- Component parsing, indexed CSV matching, AI verification/search/review, model
  rotation, and detailed trace logging stay in `src/core/drug_matching`.
- Live-order AI decision policy stays in `src/core/order_ai_matching.py`,
  `src/core/order_ai_flow.py`, and `src/core/order_ai_verify.py`; Tawreed only
  invokes it and writes trace rows.
- Live-order AI safety checks stay in `src/core/order_ai_safety.py`; AI verify
  and AI search cannot activate a match without an orderable id or with a local
  component mismatch.
- Per-run AI provider cooldown stays in
  `src/core/drug_matching/ai_provider_cooldown.py`; repeated provider
  rate-limit or invalid JSON attempts disable that provider's rotation attempts
  for the active verifier.
- Manual-review correction import stays in `src/core/manual_review_hints.py`
  with `tools/import_manual_review_hints.py`, exporting approved
  `correct_store_product_id` rows into reusable JSON hints.
- Tawreed product search uses `src/tawreed/tawreed_product_search_select.py` to
  fall back from partial API rows to DOM candidates when API rows lack
  orderable store product ids.
- Live-order matching now rejects otherwise-accepted candidates that lack an
  orderable Tawreed id, while preserving earlier lexical/component rejection
  reasons for diagnostics.
- Accepted live-search candidates use a stable winner sort key that includes
  score, exactness, overlap, numeric agreement, stock, discount, price, and id.
- Equal accepted candidates with different orderable ids now become an
  explicit ambiguity instead of an arbitrary winner.
- Fuzzy/non-exact live-search matches reject unrequested numeric additions except
  a single percentage strength marker, reducing unsafe variant acceptance.
- Numeric matching now extracts digit groups from attached unit tokens such as
  `5MG` or `30TAB`, reducing false numeric mismatches.
- Liquid per-dose markers such as `100 MG / 5 ML` do not block otherwise valid
  fuzzy matches when the requested item already contains an ML volume.
- Component parsing now covers audited false-negative formats for compact
  percent/form tokens, OCR `6O ML` volumes, `CONCOR PLUS`, `EPOETIN SEDICO`,
  `BEBELAC BEBEJUNIOR`, and generic eye/nasal drops wording.
- Order AI artifact row shaping stays in `src/core/order_ai_trace_rows.py` and
  `src/core/order_run_artifact_rows.py`.
- Order winner artifact fields stay in `src/core/order_winner_fields.py` and
  include the selected orderable id, stock, price, store, and tie-break reason.
- Order artifact writing and worker partition merging stay in
  `src/tawreed/tawreed_order_run_artifacts.py` and
  `src/tawreed/order_worker_artifact_merger.py`.
- Artifact CSV/XLSX schema normalization stays in `src/tawreed/tawreed_artifacts.py`;
  worker CSV union merging stays in `src/tawreed/order_result_merger.py`.
- Run-scoped artifact paths stay in `src/core/artifact_run.py`.
- Shared candidate-level trace rows and async logging setup stay in
  `src/core/matching_trace.py`.
- Matching trace field expansion stays in `src/core/matching_trace_fields.py`;
  trace rows include reason codes, orderable-id flags, and score breakdown
  columns for easier audit grouping.
- Queue-backed matching logging is available through
  `src/core/matching_trace.py::async_matching_logging`, which guarantees the
  listener is stopped after use.

## [ORPHANS & PENDING]

- Last failed live run `artifacts/run-control/order/order_output_1778696048.log`
  exposed artifact schema failures, not a matching decision failure. Regression
  tests now cover mixed order AI trace rows and mixed worker schemas.
- `tools/list_all_violations.py` still reports baseline size/docstring debt; this
  is tracked for staged cleanup after the runtime fix.
- Safe `remove-cart` live smoke did not remove anything, but the saved Tawreed
  session did not expose the order surface for that command. Re-run
  `run.py auth --profile wardany` before the next cart-removal live check.

## [VALIDATION]

- `.venv/bin/python -m unittest discover -s tests -q`: 238 passed.
- `.venv/bin/python tools/rule_audit.py`: `rule_audit_ok`,
  `baseline_violations_remaining:160`.
- CLI help checks succeeded for `run.py`, `order`, `remove-cart`,
  `export-products`, and `match-products`.
- Smoke run succeeded:
  `.venv/bin/python run.py match-products --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 5 --no-ai --trace --output artifacts/wardany/match_products_smoke_after_schema_fix.csv`.
- Streamlit started locally on `http://127.0.0.1:8502` and returned HTTP 200.
- Safe live smoke succeeded without changing the cart:
  `.venv/bin/python run.py order --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 1 --match-only --fast-search`.
- Safe AI order smoke succeeded without API keys and wrote `order_ai_trace` plus
  `order_item_summary` CSV/TXT files:
  `.venv/bin/python run.py order --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 1 --match-only --fast-search --ai --provider custom --api-key ''`.
- Read-only export smoke succeeded:
  `.venv/bin/python run.py export-products --profile wardany --limit 5`.
- Post-cleanup regression check succeeded:
  `.venv/bin/python -m unittest tests.test_cart_removal_items tests.test_prevented_items -q`.
- Phase validation harness added:
  `.venv/bin/python tools/phase_validation.py` runs compileall, unittest, and
  rule audit as the repeated post-phase baseline.
- Unit-test execution inside phase validation uses `tools/run_unit_tests.py` to
  silence bare Streamlit logging noise before importing UI tests.
- Phase 9 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 248 unit tests plus
  compileall and rule audit.
- Phase 10 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 249 unit tests plus
  compileall and rule audit.
- Phase 11 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 252 unit tests plus
  compileall and rule audit.
- Phase 12 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 254 unit tests plus
  compileall and rule audit.
- Phase 13 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 256 unit tests plus
  compileall and rule audit.
- Phase 14 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 258 unit tests plus
  compileall and rule audit.
- Phase 15 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 260 unit tests plus
  compileall and rule audit.
- Phase 16 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 261 unit tests plus
  compileall and rule audit.
- Phase 17 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 261 unit tests with
  Streamlit warning noise suppressed, plus compileall and rule audit.
- Phase 18 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 261 unit tests plus
  compileall and rule audit after splitting order AI verification flow.
