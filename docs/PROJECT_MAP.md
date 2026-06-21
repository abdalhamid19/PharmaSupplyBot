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

- **NEW:** Order runs now support precision row selection via `--start-item` and `--end-item` arguments, allowing users to select an exact slice of rows from the uploaded Excel sheet. This is fully integrated into the Streamlit GUI under "Advanced Options".
- `run.py order` keeps the live Tawreed search flow: it searches Tawreed per item,
  evaluates candidates through `src/core/product_matching.py`, then can optionally
  run active AI verify/search/review with strict thresholds via `--ai`.
- Order AI is opt-in. Accepted AI decisions can correct/select the active match;
  review only vetoes explicit incorrect/disagreement/conflict decisions rather
  than blocking an otherwise correct match solely for low review confidence.
- AI candidates that semantically match but lack `storeProductId` are surfaced as
  `matched-but-unavailable` with `candidate_not_orderable` manual-review
  metadata instead of disappearing as generic no-match rows.
- Order matching now has explicit `safe` and `aggressive` risk policies.
  Aggressive matches remain flagged for manual review and can either be staged
  or added to cart with manual-review metadata, depending on the selected action.
- Manual-review rows can save `approved_match`, `needs_correction`, or
  `not_matching` decisions. Saved `not_matching` choices block the same rejected
  candidate in later matching and can drive cart removal.
- Corrected manual-review rows can be re-searched with
  `order --from-manual-review-corrections <manual_review.csv>` or from the
  Streamlit Manual Review action; this runs order matching in match-only mode.
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
- Streamlit Order exposes the matching risk policy and flagged-match action used
  by the CLI.
- Streamlit Manual Review can save decisions and start a current-run
  `not_matching` cart-removal flow from edited rows.
- Streamlit Results summarizes order AI trace phases/statuses/provider errors
  before rendering the full trace table.
- New command outputs use `artifacts/<command>/<profile>/<run_id>/` with
  timestamped files. Old flat outputs were moved under `artifacts/legacy/...`.

## [ARCHITECTURE]

- CLI parsing and command dispatch stay in `src/cli`.
- Streamlit presentation and subprocess orchestration stay in `src/ui`.
- Tawreed browser automation stays in `src/tawreed`.
- Optional Tawreed API execution stays in `src/tawreed/tawreed_api*.py`. The
  `auto` backend tries a locally discovered API contract from `state/` and
  falls back to browser automation when the contract is incomplete.
- Tawreed API defaults/discovery/contract merging live in
  `src/tawreed/tawreed_api_defaults.py`,
  `src/tawreed/tawreed_api_discovery.py`, and
  `src/tawreed/tawreed_api_contract_merge.py`; product search has a safe default
  for Tawreed's `stores/products/search/similar5` endpoint, while mutation
  endpoints still require trusted captured contracts.
- Shared live-search scoring stays in `src/core/product_matching.py`.
- Shared candidate id normalization stays in `src/core/candidate_identity.py` so
  matching, AI, and artifacts agree on orderable Tawreed ids.
- Candidate ids are orderable only when they come from Tawreed store-product
  fields such as `storeProductId`/`productStoreId` or their nested metadata
  aliases; generic `id` is not treated as safe for cart actions.
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
- Tawreed live search uses a bounded per-item query cache in
  `src/tawreed/tawreed_query_cache.py`; candidate de-duplication happens before
  scoring and trace emission.
- AI JSON parsing repairs common fenced/trailing-comma JSON while leaving
  unparseable prose rejected for safety.
- Manual-review correction import stays in `src/core/manual_review_hints.py`.
  Runtime learning uses `src/core/manual_review_store.py` with a local SQLite
  file ignored by git, and `src/core/manual_review_runtime.py` applies saved
  queries or approved `storeProductId` choices before normal matching.
- Manual-review corrected-item search is implemented in
  `src/core/manual_review_corrections.py`, CLI wiring in
  `src/cli/cli_parser_manual_review_search.py`, and Streamlit launch helpers in
  `src/ui/streamlit_manual_review_search.py`.
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
- Injectable `GM` strengths are canonically compared with `MG` strengths, and
  unit-dose pack markers such as `2 ML 20 UNIT DOSE` do not block otherwise
  compatible vial matches.
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
- Manual-review removal source building stays in
  `src/core/manual_review_removal.py`; CLI wiring stays in
  `src/cli/cli_cart_removal_source.py`.
- Current-run Streamlit not-matching removal helpers stay in
  `src/ui/streamlit_manual_review_remove.py`.
- Order AI trace grouping stays in `src/core/order_ai_run_summary.py`.
- Aggressive matching bridge logic stays in
  `src/tawreed/tawreed_aggressive_matching.py`; the core risk selection remains
  in `src/core/matching_risk.py`.
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
- Candidate-level matching trace output is bounded by
  `src/core/matching_trace.py::MAX_TRACE_CANDIDATE_ROWS` to keep large runs from
  producing unbounded diagnostics.

## [ORPHANS & PENDING]

- Active remediation for `docs/full_run_program_audit_20260514_1252.md` is
  implemented. Completed: diagnostic artifact grouping, bounded match traces,
  Tawreed API contract discovery/client, `auto/api/browser` CLI+GUI backend
  selection, SQLite manual-review learning, runtime manual-review application,
  guarded API final submission, actionable candidate identity, improved
  pharmaceutical numeric/dosage rules, query caching, AI JSON repair, provider
  cooldown, candidate de-duplication, order AI review-veto correction,
  non-orderable AI candidate artifact mapping, Tawreed product-search API
  defaults/discovery, and corrected manual-review item re-search.
- Final order submission remains disabled unless `runtime.submit_order` is
  explicitly true.
- Historical `tools/list_all_violations.py` baseline debt remains outside this
  remediation scope; `tools/rule_audit.py` enforces that no new violations are
  introduced.
- Latest run audit for `20260514_2107` is documented in
  `docs/latest_run_audit_20260514_2107.md`.

## [EXTERNAL CONSTRAINTS]

- GitHub publishing depends on non-interactive credentials for
  `https://github.com/abdalhamid19/PharmaSupplyBot.git`. Local commits are made
  after each phase; `git push origin main` cannot complete in this environment
  without saved credentials or a token.
- Live cart mutation checks depend on a valid Tawreed authenticated session and
  trusted captured Tawreed mutation endpoints. Product search has a safe API
  default, but add/remove/submit still require captured contracts; `auto` falls
  back to browser automation when mutation contracts are incomplete. Final order
  submission remains disabled unless `runtime.submit_order=true`.

## [VALIDATION]

- `.venv/bin/python tools/run_unit_tests.py`: 294 passed.
- `.venv/bin/python tools/rule_audit.py`: `rule_audit_ok`,
  `baseline_violations_remaining:161`.
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
- Phase 19 validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran 261 unit tests plus
  compileall and rule audit after syncing `PROJECT_MAP.md`.
- Phase 20 validation succeeded:
  `.venv/bin/python tools/phase_validation.py --smoke` ran 262 unit tests,
  compileall, rule audit, CLI help checks, and `match-products --trace`.
- Phase 20 live-safe checks succeeded:
  `.venv/bin/python run.py order --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 1 --match-only --fast-search --ai --provider custom --api-key ''`
  accepted the first item without changing the cart, and
  `.venv/bin/python tools/import_manual_review_hints.py artifacts/order/wardany/20260513_2352/manual_review_20260513_2352.csv --output artifacts/order/wardany/20260513_2352/manual_review_hints_phase20.json`
  completed with `manual_review_hints_exported:0`.
- Latest remediation validation succeeded:
  `.venv/bin/python tools/phase_validation.py` ran compileall, 278 unit tests,
  and rule audit.
- Latest CLI/API-mode smoke succeeded: `order --help` and `remove-cart --help`
  expose `--execution-mode {auto,api,browser}`.
- Latest product matching smoke succeeded:
  `.venv/bin/python run.py match-products --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 5 --no-ai --trace --output artifacts/wardany/match_products_smoke_execution_mode.csv`.
- Latest live-safe Tawreed checks succeeded without final submit:
  `order --limit 1 --match-only --execution-mode auto` matched KENACOMB with
  browser fallback, `order --limit 1 --execution-mode auto` added one KENACOMB
  item to cart with final submission disabled, and `remove-cart
  --execution-mode auto` removed that KENACOMB cart row.
- Streamlit smoke succeeded on `http://127.0.0.1:8507` with HTTP 200.
- Latest full remediation validation succeeded on 2026-05-14:
  `.venv/bin/python tools/phase_validation.py` ran compileall, 294 unit tests,
  and rule audit.
- Limit-50 export succeeded:
  `.venv/bin/python run.py export-products --profile wardany --limit 50`
  wrote 50 unique rows to
  `artifacts/export-products/wardany/20260514_1621_2/`.
- Limit-50 standalone matching succeeded:
  `.venv/bin/python run.py match-products --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 50 --no-ai --trace`
  wrote `artifacts/match-products/wardany/20260514_1621/`; the limited 50-row
  export catalog did not cover the first 50 shortage rows, so all 50 required
  manual review in that standalone catalog comparison.
- Limit-50 Tawreed match-only succeeded:
  `.venv/bin/python run.py order --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 50 --match-only --fast-search --execution-mode auto`
  wrote `artifacts/order/wardany/20260514_1621_2/`, matched 20 rows, skipped 30
  no-result rows, and left the cart unchanged.
- AI safe smoke succeeded with configured rotation keys:
  `.venv/bin/python run.py order --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 1 --match-only --fast-search --execution-mode auto --ai --provider rotation --concurrency 1 --no-ai-preflight`
  wrote `artifacts/order/wardany/20260514_1629/` and left the cart unchanged.
- Execution-mode smokes: browser match-only succeeded in
  `artifacts/order/wardany/20260514_1629_2/`; strict API match-only failed fast
  in `artifacts/order/wardany/20260514_1629_3/` because the local contract lacks
  `product_search_url`, which is an external endpoint-discovery dependency.
- Live add-to-cart used 20 actionable match-only rows from run `20260514_1621_2`.
  `.venv/bin/python run.py order --profile wardany --excel artifacts/run-control/limit50_20260514_1621_2/live_add.xlsx --limit 50 --fast-search --execution-mode auto --item-workers 1`
  wrote `artifacts/order/wardany/20260514_1626/`, added 18 rows, skipped 2
  out-of-stock rows, and did not submit the final order because
  `runtime.submit_order=false`.
- Live remove-cart cleaned the same additions:
  `.venv/bin/python run.py remove-cart --profile wardany --excel artifacts/run-control/limit50_20260514_1621_2/live_remove_added.xlsx --execution-mode auto --item-workers 1`
  wrote `artifacts/remove-cart/wardany/20260514_1627/` and removed 18/18 rows.
- Streamlit smoke succeeded on `http://127.0.0.1:8765` with HTTP 200.
- Artifact comparison against `20260514_1252`: new Limit-50 match-only
  `match_log_all` is 3.65 MB versus 63.98 MB in the 300-row audit run, new
  `matching_trace` is 5.25 MB versus 50.60 MB, and the new no-AI/AI-smoke
  traces recorded no `429` or `invalid_json` provider errors.
- Latest no-results remediation validation succeeded on 2026-05-14:
  `.venv/bin/python tools/phase_validation.py` ran compileall, 309 unit tests,
  and rule audit. CLI help succeeded for `run.py`, `order`, `remove-cart`,
  `export-products`, and `match-products`.
- Limit-30 export succeeded:
  `.venv/bin/python run.py export-products --profile wardany --limit 30`
  wrote 30 unique rows to
  `artifacts/export-products/wardany/20260514_2047_2/`.
- Limit-30 standalone catalog matching succeeded:
  `.venv/bin/python run.py match-products --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 30 --no-ai --trace`
  wrote `artifacts/match-products/wardany/20260514_2047/`; the deliberately
  limited 30-row export catalog did not cover the shortage rows, so standalone
  catalog matching stayed at 0/30.
- Limit-30 Tawreed live-search match-only succeeded:
  `.venv/bin/python run.py order --profile wardany --excel data/input/order_items/shortage_report_total_20260502.xlsx --limit 30 --match-only --fast-search --execution-mode auto`
  wrote `artifacts/order/wardany/20260514_2054_2/`, matched 21 rows, separated
  4 non-orderable rows, left 5 true no-result/manual-review rows, and left the
  cart unchanged. For the same first 30 rows, run `20260514_1852` had 15
  matched, 14 no-results, and 1 skipped row.
- AI safe smoke was skipped because no AI provider keys were present in the
  environment; this is not a product failure. API execution still falls back in
  `auto` because the local Tawreed contract lacks externally discovered
  `product_search_url`, `add_to_cart_url`, and `remove_cart_url` fields.
- Live add-to-cart used 17 actionable matched rows from run `20260514_2054_2`.
  `.venv/bin/python run.py order --profile wardany --excel artifacts/order/wardany/20260514_2054_2/live_actionable_limit30_20260514_2054_2.xlsx --limit 30 --fast-search --execution-mode auto`
  wrote `artifacts/order/wardany/20260514_2057/`, added 17/17 rows, and did
  not submit the final order because `runtime.submit_order=false`.
- Live remove-cart cleaned the same additions after adding a longer Tawreed
  session-surface wait:
  `.venv/bin/python run.py remove-cart --profile wardany --excel artifacts/order/wardany/20260514_2054_2/live_actionable_limit30_20260514_2054_2.xlsx --execution-mode auto`
  wrote `artifacts/remove-cart/wardany/20260514_2101/` and removed 17/17 rows.
- Streamlit smoke succeeded on `http://localhost:8765` with HTTP 200.
- Current remediation added detailed manual-review artifact fields, aggressive
  flagged matching controls, saved not-matching filtering, CLI/GUI not-matching
  cart removal, and bounded matching trace output. Latest validation:
  `.venv/bin/python tools/phase_validation.py` ran compileall, 319 unit tests,
  and rule audit successfully.
- Follow-up remediation added Streamlit aggressive matching controls, a
  current-run Manual Review removal action, and order AI/API trace summaries.
- Latest validation succeeded:
  `.venv/bin/python tools/phase_validation.py --smoke` ran compileall, 323 unit
  tests, rule audit, CLI help checks, and a match-products smoke. Streamlit
  started on `http://127.0.0.1:8765` and returned HTTP 200.
- Order AI/API/manual-review remediation validation succeeded:
  `.venv/bin/python -m pytest tests/test_order_ai_matching.py
  tests/test_order_blocked_candidate_artifacts.py
  tests/test_tawreed_api_execution_mode.py
  tests/test_manual_review_corrections.py tests/test_cli_parser.py -q` covered
  AI review veto behavior, non-orderable artifact mapping, Tawreed API
  execution-mode discovery/defaults, manual-review corrected search, and parser
  wiring.
- Final rule-audit cleanup split long helpers in
  `src/core/drug_matching/verifier.py` and
  `src/core/drug_matching/pipeline.py` with focused conflict tests passing:
  `.venv/bin/python -m pytest tests/test_ai_decision_conflicts.py -q`.
- Latest final validation succeeded:
  `.venv/bin/python tools/phase_validation.py --smoke` ran compileall, 352 unit
  tests, rule audit (`baseline_violations_remaining:160`), CLI help checks, and
  a `match-products --trace` smoke.
- Follow-up CLI parser cleanup split order runtime arguments and match-products
  argument/API-config helpers without changing command options. Validation:
  `.venv/bin/python tools/run_unit_tests.py` ran 352 tests, and
  `.venv/bin/python tools/rule_audit.py` reports
  `baseline_violations_remaining:157`.
