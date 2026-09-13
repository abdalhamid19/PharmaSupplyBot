# Unified Tawreed/Excel Target Order Policy Implementation Plan

> **Historical plan note:** The warehouse-mode options described below were
> later consolidated. Current runs support `lowest_purchase_price` only; the
> older mode names remain here solely as implementation history.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Tawreed cart execution and Run Results use one deterministic policy: a valid Excel Target offer blocks Tawreed when its purchase price is lower or within one EGP, while the selected Tawreed mode controls allocation only when Tawreed remains eligible.

**Architecture:** Add one pure allocation/policy module that ranks valid Tawreed offers, applies the Excel Target gate, and produces planned allocations. Both API and browser multi-store flows call it; `ordered_qty` is written only from successful cart additions. Run Results will present actual allocations separately from price-comparison snapshots and will label Excel-deferred items explicitly.

**Tech Stack:** Python, dataclasses, SQLite order-runs persistence, pytest, Streamlit read-only queries.

**Spec:** User requirements in the 2026-09-12 conversation: actual-cart report, Excel Target diversion when its purchase price is lower or within one EGP, and `first_available` using the first available Tawreed store while preserving partial-quantity behavior.

## Global Constraints

- Preserve the existing `preferred_warehouses` order in `state/config.yaml`.
- `ordered_qty` means quantity successfully added to the Tawreed cart; an Excel Target comparison must never fabricate Tawreed ordered quantity.
- Excel Target diversion requires a valid persisted purchase price; missing or invalid prices do not block Tawreed.
- The Excel/Tawreed threshold is strict `< 1.0` EGP; equal prices are included because their difference is zero.
- Existing user changes and input files in the dirty worktree must remain untouched.
- API and browser multi-store flows must use identical selection semantics.

---

### Task 1: Encode and test the shared price/gate/allocation policy

**Files:**
- Create: `src/core/ordering/warehouse_order_policy.py`
- Test: `tests/core/ordering/test_warehouse_order_policy.py`

**Interfaces:**
- Consumes: normalized offer dictionaries containing `source`, `store_key`, `store_product_id`, `store_name`, `available_qty`, `purchase_price`, `source_label`.
- Produces: `AllocationPlan` and `AllocationLine` dataclasses plus `plan_tawreed_allocations(...)` and `excel_target_blocks_tawreed(...)`.

- [x] **Step 1: Write failing unit tests for Excel diversion.**

  Test these exact cases:
  - Excel at 90 and Tawreed at 100 blocks.
  - Excel at 100 and Tawreed at 100 blocks.
  - Excel at 100.50 and Tawreed at 100 blocks because the difference is below one EGP.
  - Excel at 101 and Tawreed at 100 does not block because the difference is exactly one EGP.
  - Missing/invalid Excel price never blocks.

- [x] **Step 2: Write failing unit tests for Tawreed allocation modes.**

  Test these exact cases:
  - `lowest_purchase_price` chooses the lower valid purchase price.
  - Tawreed prices within one EGP resolve by `preferred_warehouses` order.
  - `first_available` preserves the incoming Tawreed offer order and ignores price for store selection.
  - A first store with stock 3 and requested quantity 10 receives 3, then the next eligible store receives the remaining 7.
  - Zero stock, missing price, and non-finite prices are excluded.
  - Excel Target is never returned as a Tawreed allocation line.

- [x] **Step 3: Run the focused tests and verify they fail for the missing module/API.**

  Run: `python -m pytest tests/core/ordering/test_warehouse_order_policy.py -q`

- [x] **Step 4: Implement the pure policy module.**

  Use explicit dataclasses:

  ```python
  @dataclass(frozen=True)
  class AllocationLine:
      store: dict[str, Any]
      quantity: int
      reason: str

  @dataclass(frozen=True)
  class AllocationPlan:
      blocked_by_excel_target: bool
      excel_purchase_price: float | None
      reason: str
      allocations: tuple[AllocationLine, ...]
      remaining_qty: int
  ```

  Implement the gate as `excel_price < tawreed_reference_price + 1.0`, where the reference price is the lowest valid Tawreed purchase price when the gate is evaluated independently of the selected Tawreed mode. Implement `first_available` as stable input-order allocation and `lowest_purchase_price` as price ordering with the configured warehouse order resolving Tawreed near-ties.

- [x] **Step 5: Run the focused tests and verify they pass.**

  Run: `python -m pytest tests/core/ordering/test_warehouse_order_policy.py -q`

---

### Task 2: Wire the shared policy into API and browser Tawreed ordering

**Files:**
- Modify: `src/tawreed/api/tawreed_api_flow_multistore.py`
- Modify: `src/tawreed/products/tawreed_products_flow.py`
- Modify: `src/core/ordering/excel_target_cart_gate.py`
- Modify: `src/tawreed/order/tawreed_order_processing.py`
- Test: `tests/tawreed/api/test_tawreed_api_excel_target_cart_gate.py`
- Test: `tests/tawreed/store/test_tawreed_store_choice.py`
- Test: `tests/core/ordering/test_excel_target_cart_gate.py`

**Interfaces:**
- Consumes: Task 1 policy functions and current run-scoped Excel Target database.
- Produces: identical allocation behavior for API and browser multi-store paths, plus a `deferred_to_excel_target` reason for persistence.

- [x] **Step 1: Add failing integration tests for the new near-tie gate and partial `first_available` allocation.**

  Assert that a Tawreed add is not attempted when Excel is 0.50 EGP higher, and that a request of 10 adds 3 from the first store and 7 from the next store in `first_available` mode.

- [x] **Step 2: Replace per-store gate checks with a single preflight decision.**

  Load all Tawreed store rows, evaluate the Excel gate before any cart mutation, and return a blocked/deferred result without calling `add_to_cart` or opening a quantity dialog. Do not call the old single-store gate once per selected store.

- [x] **Step 3: Use the shared allocator in both API and browser multi-store flows.**

  Pass the same store rows, mode, minimum discount, and preferred warehouse list into the policy. Execute each returned allocation line only after the whole plan passes the Excel gate. Preserve the existing UI/API quantity-entry behavior.

- [x] **Step 4: Keep legacy single-store behavior safe.**

  Where Tawreed purchase price cannot be read structurally, preserve the conservative behavior: a valid Excel Target price causes `deferred_to_excel_target`; otherwise continue the legacy path. Do not claim that legacy execution selected a price winner.

- [x] **Step 5: Run focused API/browser/gate tests.**

  Run: `python -m pytest tests/core/ordering/test_warehouse_order_policy.py tests/core/ordering/test_excel_target_cart_gate.py tests/tawreed/api/test_tawreed_api_excel_target_cart_gate.py tests/tawreed/store/test_tawreed_store_choice.py -q`

---

### Task 3: Persist actual execution status without conflating price winners

**Files:**
- Modify: `src/core/database/order_runs_writer.py`
- Modify: `src/core/database/order_runs_stores.py`
- Modify: `src/core/database/order_runs_views.py`
- Modify: `src/tawreed/matching/tawreed_order_summary.py`
- Test: `tests/core/database/test_order_runs_schema_behaviour.py`
- Test: `tests/core/database/test_warehouse_winners.py`

**Interfaces:**
- Consumes: successful allocation lines and deferred decisions from Task 2.
- Produces: `ordered_qty` reflecting actual Tawreed additions, while `is_winner`/`run_warehouse_winners` remain comparison metadata.

- [x] **Step 1: Add failing persistence tests for deferred and partial outcomes.**

  Assert that a deferred Excel item has `ordered_qty=0`, a dedicated reason/status, and no selected Tawreed allocation. Assert that a partial multi-store add stores exactly the quantities successfully added by each store and does not copy the requested quantity to every offer.

- [x] **Step 2: Persist deferred-to-Excel status explicitly.**

  Use a stable status such as `deferred-to-excel-target`; keep `requested_qty` unchanged and set `ordered_qty=0`. Do not classify the item as `no-results` or `not-orderable`.

- [x] **Step 3: Ensure successful cart additions write actual allocation quantities only.**

  Keep comparison winner fields separate from ordered quantities. Do not allow cross-source reconciliation to overwrite the actual selection fields used by the report.

- [x] **Step 4: Update summary aggregates to scope actual order metrics to the Tawreed execution source and distinct items.**

  Keep source-level diagnostics available, but make the user-facing “added” and “ordered” metrics use distinct `item_key` counts and actual `ordered_qty` values. Include deferred Excel items in a separate count.

- [x] **Step 5: Run database tests and verify existing winner-comparison behavior remains covered.**

  Run: `python -m pytest tests/core/database/test_order_runs_schema_behaviour.py tests/core/database/test_warehouse_winners.py -q`

---

### Task 4: Make Run Results show the actual Tawreed basket

**Files:**
- Modify: `src/core/database/order_runs_read_sql.py`
- Modify: `src/core/database/order_runs_read.py`
- Modify: `src/ui/views/run_db/streamlit_run_db_page.py`
- Modify: `src/ui/views/run_db/streamlit_warehouse_winners.py`
- Modify: `src/ui/views/run_db/streamlit_run_kpis.py`
- Test: `tests/ui/views/run_db/test_warehouse_winner_export.py`
- Create: `tests/ui/views/run_db/test_run_actual_basket.py`

**Interfaces:**
- Consumes: actual `ordered_qty` and deferred statuses from Task 3.
- Produces: an actual-basket report whose store counts match successful Tawreed additions, plus a clearly labeled optional price-comparison section.

- [x] **Step 1: Write failing read/UI tests.**

  Use fixture rows where a price winner differs from the ordered store and assert that the actual-basket query reports the ordered store only. Assert that `deferred-to-excel-target` is visible as deferred and not added.

- [x] **Step 2: Add a read query for actual allocations.**

  Aggregate `run_item_stores` rows with `ordered_qty > 0`, scoped to Tawreed store-detail rows, grouped by `store_key`, with `count(distinct item_key)` and `sum(ordered_qty)`.

- [x] **Step 3: Render “السلة الفعلية” before comparison analytics.**

  Show store, distinct item count, ordered quantity, and item-level allocation rows. Rename the existing warehouse-winner section to “مقارنة الأسعار المحفوظة” and add a caption that it is not the basket.

- [x] **Step 4: Add a deferred Excel section and correct KPI labels.**

  Use `added_to_cart` only for actual successful additions, show deferred Excel separately, and avoid presenting `run_warehouse_winners` counts as cart contents.

- [x] **Step 5: Run UI/read tests.**

  Run: `python -m pytest tests/ui/views/run_db/test_run_actual_basket.py tests/ui/views/run_db/test_warehouse_winner_export.py -q`

---

### Task 5: Full regression verification and documentation

**Files:**
- Modify: `docs/superpowers/plans/2026-09-12-unified-tawreed-order-policy.md`
- Create: `docs/unified-tawreed-order-policy.md`

- [x] **Step 1: Document the final business rules and status meanings.**

  Include examples for lower Excel price, Excel near-tie, full Tawreed stock, partial stock, and `first_available` allocation.

- [x] **Step 2: Run the complete relevant test suite.**

  Run: `python -m pytest tests/core/ordering tests/core/database tests/tawreed/api tests/tawreed/store tests/ui/views/run_db -q`

- [x] **Step 3: Inspect the diff and confirm no pre-existing user files changed.**

  Run: `git status --short` and `git diff --stat`; review only files listed in this plan as task changes.

- [x] **Step 4: Record verification results in this plan.**

Verification on 2026-09-12:

```text
python -m pytest tests/core/ordering tests/core/database tests/tawreed/api \
  tests/tawreed/store tests/tawreed/products tests/ui/views/run_db tests/ui/order -q
354 passed, 9 skipped in 22.76s
```

The pre-existing dirty configuration, database, artifacts, and input worktree
files were retained. No live Tawreed cart mutation was performed during
verification.

  Add the exact test command and pass count after implementation.
