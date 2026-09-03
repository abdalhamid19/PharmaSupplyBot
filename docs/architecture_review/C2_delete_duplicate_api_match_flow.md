# C2 — Delete the duplicate API match flow

**Strength:** Strong
**Tag:** in-process

## Files

- `src/tawreed/api/tawreed_api_matching.py` (~150 lines, near-dead copy)
- `src/tawreed/api/tawreed_api_flow_matching.py` (~215 lines, the live one)
- `src/tawreed/api/tawreed_api_flow.py` (facade re-exporting 12 names, 10 of them `_private`)

## Problem

`tawreed_api_matching.py` duplicates `tawreed_api_flow_matching.py` nearly line-for-line. Both define `require_api_match`, `_check_api_match`, `_search_products_timed`, `_manual_review_decision_timed`, `_api_match_decision`, `_handle_api_no_match`, `_raise_non_orderable_exception`, `_has_only_non_orderable_candidates`, `_accepted_api_match`, `_is_saved_manual_review_match` — identical docstrings and an identical `999.0` diagnostic fabrication (`api_matching.py:107-122` ≡ `flow_matching.py:130-160`). Cross-imports reach back into `flow_matching._require_orderable_api_match`. **No `src/` module imports `tawreed_api_matching`** — only one private helper in `tests/tawreed/api/test_tawreed_api_execution_mode.py:16` and the `rule_audit` allowlist. Meanwhile `tawreed_api_flow.py` re-exports *all twelve* names of `flow_matching`, including ten `_private` functions, in `__all__` — an interface that is the implementation.

**Deletion test:** delete `tawreed_api_matching.py` and the duplication vanishes; no `src/` import breaks. Delete `tawreed_api_flow.py` and complexity just moves to different import paths — shallow facade, earn nothing.

## Solution

1. Delete `tawreed_api_matching.py`.
2. Shrink `tawreed_api_flow.py` to the three public operations: `require_api_match`, the order/result entry, and the cart-removal entry.
3. Parameterise `require_api_match(item, search, policy)` instead of `(bot, api, item, require_available)`. The `bot`/`api` pair is exactly what prevents tests from calling the public entry point (which is why the test imports `_has_only_non_orderable_candidates` directly).

## Before / After

### Before — two identical stacks, the facade is the implementation

```
  ┌─────────────────────────┐    ┌─────────────────────────┐
  │ tawreed_api_matching.py │    │ tawreed_api_flow_       │
  │  require_api_match      │    │  matching.py            │
  │  _check_api_match       │    │  require_api_match      │
  │  _search_products_timed │    │  _check_api_match       │
  │  _manual_review_dec_…   │    │  _search_products_timed │
  │  _api_match_decision    │    │  _manual_review_dec_…   │
  │  _handle_api_no_match   │    │  _api_match_decision    │
  │  _has_only_non_order…   │ ←→ │  _has_only_non_order…   │
  │  _accepted_api_match    │    │  _accepted_api_match    │
  │  _is_saved_manual_…     │    │  _is_saved_manual_…     │
  │  (999.0 fabric)         │    │  (999.0 fabric)         │
  └─────────────────────────┘    └─────────────────────────┘
              │  imported by 0 src files
              ▼
  ┌──────────────────────────────────────────────────────┐
  │ tawreed_api_flow.py   (__all__ = 12 names, 10 _priv) │
  └──────────────────────────────────────────────────────┘
```

### After — one stack, the facade is a real interface

```
                          ┌──────────────────────────┐
                          │ require_api_match(       │   ← interface
                          │   item, search, policy)  │     (3 params)
                          └────────────┬─────────────┘
                                       │ deep implementation
                                       ▼
                          ┌──────────────────────────┐
                          │ check · search · decide  │
                          │ manual-review · no-match │
                          │ provenance · policy      │
                          └──────────────────────────┘
                                       ▲
                                       │ 2 adapters
                          ┌────────────┴─────────────┐
                          ▼                          ▼
                  ApiSearchAdapter         BrowserSearchAdapter
                  (tawreed_api.py)         (Playwright page)
```

## Wins

- delete ~150 duplicated lines (the deep module gets ~150 lines deeper, the shallow one disappears)
- interface stops re-exporting `_private` names
- tests hit one interface, not `_require_orderable_api_match` directly
- seam appears: the search callable becomes injectable
- unlocks C3 (one match loop, two adapters) by removing the duplicate that C3 would otherwise have to keep
