# Excel Target Cart Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent a real Tawreed cart addition when any accepted Excel Target match has a purchase price less than or equal to the Tawreed offer being selected.

**Architecture:** Excel Target matches are persisted before Tawreed profiles run in `run_item_stores`. A focused price-gate service will query the cheapest accepted Excel Target offer for an item, compare it to the concrete Tawreed candidate with the existing price resolver, and block immediately before every cart mutation. Winner reconciliation stays reporting-only.

**Tech Stack:** Python, SQLite, pytest, `resolve_store_prices`.

**Spec:** `docs/superpowers/plans/2026-09-09-excel-target-cart-gate.md`

## Global Constraints

- Only real orders are gated; `--match-only` is unchanged.
- Block exactly when `excel_purchase_price <= tawreed_purchase_price`.
- NULL Excel purchase prices never block.
- All selected Excel Targets, API/browser modes, and multi-store choices are covered.
- A block records a clear skip reason and performs no add-to-cart mutation.

---

## Parallel Subagent and Skill Assignment

The implementation is intentionally split so agents work on non-overlapping files. The root agent owns the integration branch, resolves interface conflicts, runs the final suite, and performs the final review. Subagents must not edit files assigned to another lane.

| Lane | Subagent responsibility | Depends on | Recommended skills | Files owned |
|---|---|---|---|---|
| A — persistence contract | Verify the shared run key, `order_run_item_key`, DB path propagation, and Excel Target persistence. Add regression coverage. | None | `systematic-debugging`, `pytest-testing` | `src/cli/commands/cli_order_excel_target.py`, `src/core/database/order_runs_keys.py`, persistence tests |
| B — gate service | Implement the pure comparison service and SQLite query using resolved Excel purchase prices. | Lane A findings | `tdd`, `pytest-testing`, `codebase-design` | `src/core/ordering/excel_target_cart_gate.py`, gate unit tests |
| C — API ordering | Add preflight checks to single-store and multi-store API flows. Multi-store must preflight all selected choices before the first mutation to prevent partial cart additions. | Lane B interface | `tdd`, `systematic-debugging` | `src/tawreed/api/tawreed_api_flow_cart.py`, `src/tawreed/api/tawreed_api_flow_multistore.py`, API tests |
| D — browser ordering | Add equivalent checks to product-page single/multi-store flows and define the conservative legacy selector-flow behavior. | Lane B interface | `tdd`, `webapp-testing`, `playwright` only if a live UI test is required | `src/tawreed/products/tawreed_products_flow.py`, `src/tawreed/order/tawreed_order_processing.py`, browser tests |
| E — integration/reviewer | Verify shared-run E2E behavior, docs, regressions, and clean-code findings after A–D merge. | A–D | `clean-code-guard`, `code-review`, `systematic-debugging` | `tests/cli/commands/test_excel_target_e2e.py`, `README.md`, review report |

Execution order:

1. Spawn Lane A and Lane B in parallel; Lane B uses the existing DB contract provisionally and incorporates Lane A’s findings before its final patch.
2. After Lane B’s public interface is fixed, spawn Lane C and Lane D in parallel because their files do not overlap.
3. After C and D finish, spawn Lane E for integration tests and review. The root agent resolves any findings and owns the final full-suite run.

Agent protocol:

- Each lane starts by reading the relevant skill file completely and announcing which skill it is applying.
- Each lane writes failing tests before implementation, runs its focused tests, and reports changed files, commands, and remaining risks.
- Agents do not reset, stash, or overwrite unrelated work. If a shared-file conflict appears, stop and report it to the root agent.
- Luna `extra-high` is preferred for the design/review lanes (A, B, and E) when available; use the repository’s normal high-quality model for mechanical test additions.
- Review gates: root reviews Lane A/B interfaces before C/D start, then Lane E reviews all merged changes before completion.

Useful skills and when to apply them:

- `writing-plans`: maintain this plan and dependency graph before code changes.
- `tdd`: enforce red → green → refactor for each gate and flow.
- `pytest-testing`: fixtures for SQLite rows, API mocks, browser-flow mocks, and focused regression commands.
- `systematic-debugging`: investigate DB-path/run-key mismatches and any unexpected cart mutation before proposing changes.
- `codebase-design`: keep the gate as a deep, reusable module rather than duplicating SQL/comparison logic in API and browser flows.
- `webapp-testing` / `playwright`: only for a live browser smoke check; unit tests should remain the primary fast gate.
- `clean-code-guard`: final pass for duplicated checks, unclear skip reasons, and accidental mutation paths.
- `code-review`: final standards/spec review after the parallel lanes are merged.

---

### Task 0: Stabilize the shared-run persistence contract

**Files:**
- Modify: `src/cli/commands/cli_order_excel_target.py:804-900`
- Inspect/modify: `src/core/database/order_runs_keys.py:15`
- Test: `tests/core/database/test_order_runs_excel_target_e2e.py`

**Interfaces:**
- Produces a guarantee that Excel Target rows and the later gate use the same `run_key`, stable item key, and configured database path.

- [ ] **Step 1: Write a regression test** proving a non-default configured DB path contains the persisted Excel Target row under `source='excel_target'` and the expected item key.
- [ ] **Step 2: Run the focused test and capture the current failure** caused by the persister falling back to the default DB path.
- [ ] **Step 3: Pass `app_config.database.persistence_options()` through `_build_db_persister`/`record_run_item` and use `order_run_item_key` consistently.
- [ ] **Step 4: Run `tests/core/database/test_order_runs_excel_target_e2e.py` and commit the persistence-only change.

This task must complete before Task 1’s final implementation, because a correct comparison against the wrong database would silently allow cart mutations.

---

### Task 1: Reusable price gate

**Files:**
- Create: `src/core/ordering/excel_target_cart_gate.py`
- Test: `tests/core/ordering/test_excel_target_cart_gate.py`

**Interfaces:**
- Produces `CartGateDecision(blocked: bool, excel_purchase_price: float | None, reason: str)`.
- Produces `ExcelTargetCartGate.evaluate(run_key: str, item: Item, tawreed_store: dict[str, Any]) -> CartGateDecision`.

- [ ] **Step 1: Write the failing tests**

```python
def test_blocks_when_excel_is_lower_or_equal(tmp_path):
    gate = ExcelTargetCartGate(tmp_path / "runs.db")
    write_excel_offer(gate, "wardany/run-1", ITEM, purchase_price=100)
    assert gate.evaluate("wardany/run-1", ITEM, tawreed_store(100)).blocked

def test_allows_when_excel_is_higher_or_price_is_missing(tmp_path):
    gate = ExcelTargetCartGate(tmp_path / "runs.db")
    write_excel_offer(gate, "wardany/run-1", ITEM, purchase_price=101)
    assert not gate.evaluate("wardany/run-1", ITEM, tawreed_store(100)).blocked
```

- [ ] **Step 2: Run test red**

Run: `.venv\Scripts\python.exe -m pytest -q tests\core\ordering\test_excel_target_cart_gate.py`

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement the minimal service**

```python
def evaluate(self, run_key, item, tawreed_store):
    tawreed_price = resolve_store_prices(tawreed_store).purchase_price
    excel_price = self._lowest_excel_purchase_price(run_key, item)
    blocked = excel_price is not None and tawreed_price is not None and excel_price <= tawreed_price
    return CartGateDecision(blocked, excel_price, self._reason(excel_price, tawreed_price) if blocked else "")
```

Use Lane A’s `order_run_item_key` contract and configured DB path. Query `run_item_stores` by the same `run_key` and item key with `source = 'excel_target'`; use `MIN(purchase_price)` and ignore NULLs or missing run keys. Never compare the raw Excel `salePrice`; use the persisted resolved `purchase_price` including public-price/discount derivation.

- [ ] **Step 4: Run tests green**

Run: `.venv\Scripts\python.exe -m pytest -q tests\core\ordering\test_excel_target_cart_gate.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/core/ordering/excel_target_cart_gate.py tests/core/ordering/test_excel_target_cart_gate.py; git commit -m "feat: add Excel Target cart price gate"`

### Task 2: Gate API cart calls

**Files:**
- Modify: `src/tawreed/api/tawreed_api_flow_cart.py:35-98`
- Modify: `src/tawreed/api/tawreed_api_flow_multistore.py:47-100`
- Test: `tests/tawreed/api/test_tawreed_api_excel_target_cart_gate.py`

**Interfaces:**
- Consumes Task 1 using `active_order_run_key()` and the selected store dictionary.
- Produces `bot.skip_item_exception(decision.reason)` before `api.add_to_cart`.

- [ ] **Step 1: Write the failing tests**

```python
def test_api_does_not_add_when_excel_is_equal(mocker, bot, item):
    mocker.patch("...ExcelTargetCartGate.evaluate", return_value=CartGateDecision(True, 100, "Excel Target price wins"))
    api = mocker.Mock()
    with pytest.raises(bot.skip_item_exception):
        _add_single_item_to_cart(bot, api, matched_store(100), item, mocker.Mock())
    api.add_to_cart.assert_not_called()
```

Add the equivalent multi-store test asserting `_add_store_to_cart` is not reached.

- [ ] **Step 2: Run test red**

Run: `.venv\Scripts\python.exe -m pytest -q tests\tawreed\api\test_tawreed_api_excel_target_cart_gate.py`

Expected: FAIL because no gate runs.

- [ ] **Step 3: Add the mutation-boundary gate**

```python
decision = ExcelTargetCartGate.from_config(bot.config).evaluate(active_order_run_key(), item, tawreed_store)
if decision.blocked:
    raise bot.skip_item_exception(decision.reason)
```

Call it after the existing orderability/discount validation and immediately before every API cart mutation. In multi-store mode, preflight every store choice that would be used for the requested quantity before the first `api.add_to_cart`; if any selected choice is blocked, stop the whole item so no partial cart addition occurs.

- [ ] **Step 4: Run tests green**

Run: `.venv\Scripts\python.exe -m pytest -q tests\tawreed\api\test_tawreed_api_excel_target_cart_gate.py`

Expected: PASS with zero `api.add_to_cart` calls for blocked cases.

- [ ] **Step 5: Commit**

Run: `git add src/tawreed/api/tawreed_api_flow_cart.py src/tawreed/api/tawreed_api_flow_multistore.py tests/tawreed/api/test_tawreed_api_excel_target_cart_gate.py; git commit -m "feat: gate API cart additions by Excel Target price"`

### Task 3: Gate browser flow and prove shared-run visibility

**Files:**
- Modify: `src/tawreed/products/tawreed_products_flow.py:141-200,258-270`
- Create: `tests/tawreed/products/test_excel_target_cart_gate.py`
- Modify: `tests/cli/commands/test_excel_target_e2e.py`
- Modify: `README.md`

**Interfaces:**
- Consumes Task 1 with the selected browser store candidate.
- Produces no `_click_cart` or quantity dialog for a blocked item.

- [ ] **Step 1: Write the failing tests**

```python
def test_browser_does_not_click_cart_when_excel_is_cheaper(mocker, bot, page, item):
    mocker.patch("...ExcelTargetCartGate.evaluate", return_value=CartGateDecision(True, 90, "Excel Target price wins"))
    click = mocker.patch("src.tawreed.products.tawreed_products_flow._click_cart")
    with pytest.raises(bot.skip_item_exception):
        _open_add_to_cart_for_match(bot, page, mocker.Mock(), item, matched_store(100))
    click.assert_not_called()
```

In the existing Excel Target E2E test, persist an offer in `wardany/run-1` and assert the gate blocks a 100-price Tawreed candidate.

- [ ] **Step 2: Run tests red**

Run: `.venv\Scripts\python.exe -m pytest -q tests\tawreed\products\test_excel_target_cart_gate.py tests\cli\commands\test_excel_target_e2e.py -k cart_gate`

Expected: FAIL because browser flow opens the cart.

- [ ] **Step 3: Implement and document**

Invoke the shared gate immediately before `_click_cart` for a single store and preflight all selected stores before the first quantity dialog for multi-store. The selector-only legacy flow cannot verify Tawreed’s price; if a price-bearing Excel match exists, skip it with a clear “cannot compare legacy Tawreed price” reason rather than ordering blindly. Document that Excel Target is not ordered automatically; it blocks an equal-or-higher Tawreed cart offer.

- [ ] **Step 4: Run full relevant suite**

Run: `.venv\Scripts\python.exe -m pytest -q tests\core\ordering\test_excel_target_cart_gate.py tests\core\excel_target\test_excel_target.py tests\cli\commands\test_excel_target_e2e.py tests\tawreed\api\test_tawreed_api_excel_target_cart_gate.py tests\tawreed\products\test_excel_target_cart_gate.py tests\cli\commands\test_cli_order_sort_by_net.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add src/tawreed/products/tawreed_products_flow.py tests/tawreed/products/test_excel_target_cart_gate.py tests/cli/commands/test_excel_target_e2e.py README.md; git commit -m "feat: block browser cart additions beaten by Excel Target"`

## Self-Review

1. **Spec coverage:** Tasks cover lower-or-equal comparison, every selected Excel Target, real-order-only behavior, API/browser/multi-store routes, mutation prevention, and shared-run persistence.
2. **Placeholder scan:** The database source, comparator, call boundaries, required skip behavior, test commands, and expected results are explicit.
3. **Type consistency:** All cart paths call the same decision service with the active run key, input item, and actual Tawreed candidate.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-09-excel-target-cart-gate.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

## Execution Record (2026-09-09)

- [x] Lane A: configured order-runs DB path and stable `order_run_item_key` persistence.
- [x] Lane B: reusable inclusive (`<=`) Excel purchase-price gate with NULL-safe resolution.
- [x] Lane C: API single-store gate and multi-store preflight before any mutation.
- [x] Lane D: browser single-store gate, multi-store preflight, and conservative legacy-flow behavior.
- [x] Lane E: Luna extra-high review; fixed persistence-disabled behavior, multi-profile shared scope, item-worker propagation, and blank-price-to-zero conversion.
- [x] Focused implementation suite: 77 passed, 4 skipped.
- [ ] Full `pytest` repository run: existing unrelated collection/runtime failures remain outside this feature (the `tests` run reported 1,159 passed, 20 failed, 19 skipped).
