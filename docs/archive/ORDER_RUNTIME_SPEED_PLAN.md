# Tawreed Order Runtime Speed Plan

## Goal

Reduce `Fresh Run Analysis` time per item as far as safely possible while still checking Tawreed live data for every item. The safe policy means the program must not rely on stale saved manual-review data for stock, price, or current orderability.

## Current Findings

Latest analyzed run: `artifacts/order/wardany/20260620_2221`.

Observed timing:

- Average total item time: about `2.50s`.
- `api_search_seconds`: about `0.5s` to `1.1s`.
- `match_decision_seconds`: about `0.81s` per item before manual-review caching.
- Unaccounted time: about `0.75s` to `1.28s`.
- Some saved manual-review matches produced `match_elapsed_seconds=0`, so timing needed correction before judging performance.

Likely bottlenecks:

- Repeated manual-review DB lookups and schema checks in the hot path.
- First API request context setup cost being charged to the first item.
- Artifact and summary writes happening item by item.
- Browser/debug mode and defensive dialog cleanup when the run does not need a visible browser.

## Implementation Strategy

### 1. Fix Runtime Measurements

Add timing buckets that explain the runtime instead of hiding cost in the total:

- `api_context_init_seconds`
- `api_search_seconds`
- `dom_wait_seconds`
- `dialog_close_seconds`
- `manual_review_lookup_seconds`
- `match_decision_seconds`
- `add_to_cart_seconds`
- `artifact_write_seconds`
- `summary_build_seconds`

Rules:

- `elapsed_seconds` remains full item wall time.
- `match_elapsed_seconds` records successful matching time, including saved manual-review matches.
- Setup costs that happen before the first item are attached to the first processed item as pending setup timing.
- Streamlit shows average timing buckets plus `unaccounted_seconds`.

### 2. Remove Manual-Review DB Hot-Path Cost

Manual-review decisions are reusable metadata and should not be fetched repeatedly.

Implementation:

- Initialize `ManualReviewStore` schema once per process/database manager.
- Add `ManualReviewStore.lookup_many(items)` to load all relevant decisions for a run.
- Add a run-scoped manual-review cache activated around order and match-only execution.
- Use the cached decision in:
  - query selection
  - saved manual-review matching
  - rejected-candidate filtering
  - manual-review artifact decisions

Expected impact:

- Remove repeated CockroachDB round trips from each item.
- Reduce `match_decision_seconds` from roughly `0.8s` toward near-zero for saved manual-review matches.

### 3. Keep API Flow Warm and Browser-Free for Match-Only

Implementation:

- Keep `TawreedApiClient` as a long-lived client per run.
- Warm up `APIRequestContext` before item timing starts.
- Record warm-up cost in `api_context_init_seconds`.
- In Streamlit, when `match_only=True` and execution mode is `auto`, run with `--execution-mode api`.
- Keep browser fallback available only when the user explicitly selects browser mode or strict API is unavailable outside match-only.

Expected impact:

- Avoid opening Chromium for match-only.
- Avoid charging API context setup to every item or hiding it in the first item.

### 4. Reduce Artifact Overhead

Short-term behavior:

- Preserve all existing CSV columns and file names.
- Add timing columns at the end only.
- Continue writing current artifacts for compatibility.

Next optimization target:

- Introduce an `ArtifactBuffer` for run-scoped CSV/TXT/XLSX writes.
- Flush every fixed number of items and at run end.
- Keep match-only hot path CSV-focused.
- Defer heavy XLSX/TXT writes for real order runs where possible.

Acceptance rule:

- Artifact buffering must produce the same final files and columns as direct writes.

### 5. Improve Browser/UI Path

Implementation:

- Default Streamlit `Debug browser` to `False`.
- Do not repeat visible-table search when the winning query is already active.
- Keep DOM fallback only when API candidates are missing or not orderable.
- Keep dialog cleanup defensive on failures, but avoid unnecessary cleanup after successful adds.

Expected impact:

- Less browser startup/visibility overhead.
- Less redundant UI work in order runs.

### 6. API Add-to-Cart Discovery

Implementation:

- Broaden add-to-cart endpoint markers for discovery.
- Keep mutating API disabled unless a trusted `add_to_cart_url` and body are captured and verified.
- Do not enable API add-to-cart by default from an unknown endpoint.

Acceptance rule:

- Search-only API remains safe.
- Real cart mutation via API requires explicit trusted contract data.

## Acceptance Criteria

Run match-only on the same three items used in the latest analysis.

Targets:

- Safe first target: average item time under `1.3s`.
- Strong target: `0.7s` to `1.0s` if Tawreed API latency remains around `0.5s` to `1.1s`.
- `manual_review_lookup_seconds` should be paid mostly once during preload, not repeatedly per item.
- `match_elapsed_seconds` must be non-zero for successful saved manual-review matches.
- `unaccounted_seconds` should be below `0.3s` on average after measurement fixes and buffering.

## Test Plan

Focused tests:

- Manual-review preload uses one bulk store call for multiple items.
- Saved manual-review API matches set `last_match_elapsed_seconds`.
- API client warm-up opens one request context and does not duplicate contexts.
- Streamlit match-only auto mode emits `--execution-mode api`.
- Timing summaries include all timing buckets without removing old columns.

Regression tests:

- `tests/test_tawreed_api.py`
- `tests/test_tawreed_api_execution_mode.py`
- `tests/test_tawreed_product_search.py`
- `tests/test_tawreed_products_flow.py`
- `tests/test_tawreed_match_logs.py`
- `tests/test_streamlit_order.py`

Known test caveat:

- Full `pytest` may collect debug login scripts under `tools/debug/` if run without limiting paths.
- Some manual-review tests use the shared DB because the current CockroachDB-backed store ignores old SQLite paths.
