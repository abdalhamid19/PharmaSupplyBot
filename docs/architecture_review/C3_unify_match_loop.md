# C3 — One match loop, two search adapters

**Strength:** Strong
**Tag:** ports & adapters

## Files

- `src/tawreed/api/tawreed_api_flow_matching.py` (`require_api_match`)
- `src/tawreed/matching/tawreed_search_logic.py` (`require_product_match`, ~148 lines)
- Consumers: `src/tawreed/order/tawreed_order_match.py`, `tawreed_order_placement.py`, `src/tawreed/api/tawreed_api_flow_main.py`, `tawreed_api_flow_cart.py`

## Problem

The 6-step match-search protocol is copy-pasted between the API and browser backends:

1. `manual_review_queries(item, _search_queries_for_item(item), decision)`
2. Per-query cached search — API at `flow_matching.py:35`, browser at `search_logic.py:64`
3. `_manual_review_decision_timed` — identical function in both (`search_logic.py:81-89` ≡ `flow_matching.py:78-89`)
4. Manual-review forced match then `explain_best_product_match(item, ..., bot.config.matching)`
5. `decisive_match(bot, item, decision, ...)`
6. `write_match_log` + no-match handling with identical error strings (`"No decisive match found for '{item.name}' after {len(queries)} queries."`)

Only step 2's search mechanism varies (Playwright `search_products(bot, page, q)` vs `api.search_products(q)`) — i.e., the *only* genuine variation point is not a parameter; everything around it is duplicated. The copies have already drifted: the API copy lacks the `filter_manual_review_candidates` step that the browser copy has at `search_logic.py:99`.

The browser/API adapter seam exists conceptually (`execution_mode` in `tawreed_bot_api.py`), but the shared protocol is duplicated, so behaviour drifts independently.

## Solution

One `run_item_match(item, search_adapter, *, policy, cache, observers)` module — natural home `src/tawreed/matching/`, with `explain_best_product_match` staying in `src/core/matching`. Two adapters: `BrowserSearchAdapter(bot, page)` and `ApiSearchAdapter(api)`. `require_product_match` and `require_api_match` collapse to thin constructors of the adapter.

This depends on C2: parameterising `require_api_match(item, search, policy)` gives the search adapter its parameter slot. C2 makes C3 possible.

## Before / After

### Before — two parallel chains with the same 6 steps, drift already real

```mermaid
flowchart LR
  subgraph browser["Browser backend (search_logic.py)"]
    B1[manual_review_queries] --> B2[cached search<br/>Playwright page]
    B2 --> B3[_manual_review_decision_timed]
    B3 --> B4[explain_best_product_match]
    B4 --> B5[decisive_match]
    B5 --> B6[write_match_log + no-match]
    B6 -.filter_manual_review_candidates.-> B4
  end
  subgraph api["API backend (flow_matching.py)"]
    A1[manual_review_queries] --> A2[cached search<br/>api.search_products]
    A2 --> A3[_manual_review_decision_timed]
    A3 --> A4[explain_best_product_match]
    A4 --> A5[decisive_match]
    A5 --> A6[write_match_log + no-match]
  end
  classDef leak stroke:#dc2626,stroke-width:2px,stroke-dasharray:4 4;
  class B4 leak
```

### After — one loop, the search is the only thing that varies

```mermaid
flowchart LR
  I[item] --> R[run_item_match<br/><i>item, search_adapter, policy, cache, observers</i>]
  R -->|adapter.search| B
  R -->|adapter.search| A
  subgraph adapters
    B[BrowserSearchAdapter<br/>Playwright]
    A[ApiSearchAdapter<br/>tawreed_api]
  end
  B --> P[(steps 1,3-6<br/>one impl)]
  A --> P
  P --> O[MatchOutcome]
```

## Wins

- duplicated protocol becomes one implementation
- drift stops (the `filter_manual_review_candidates` gap closes)
- leverage: one interface, two adapters
- locality: protocol bugs fixed once, both backends benefit
- reads the seam: API vs browser is now the variation; today it is implicit in copy-paste
