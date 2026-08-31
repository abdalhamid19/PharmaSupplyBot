# C1 — Give `TawreedBot` two small interfaces

**Strength:** Strong
**Tag:** ports & adapters

## Files

- `src/tawreed/tawreed.py`
- `src/tawreed/tawreed_bot_core.py`
- `src/tawreed/tawreed_bot_api.py`
- `src/tawreed/tawreed_bot_methods.py`
- `src/tawreed/api/tawreed_api_flow*.py`
- `src/tawreed/matching/*.py`
- `src/tawreed/order/*.py`

## Problem

One module — `TawreedBot` — is the interface for everything. 30+ distinct attributes are touched by ~40 flow functions (`bot.config` ×34, `bot.selectors` ×31, `bot.skip_item_exception` ×26, `bot.profile_key` ×26, `bot.last_match_decision` ×14, `bot.last_match_elapsed_seconds` ×10, `bot.no_results_exception` ×5, plus the privates `_stop_before_item`, `_reset_last_item_state`, `_record_pending_item_timing`). Flows return results by *mutating* bot state instead of returning values (`tawreed_api_flow_matching.py:57`, `tawreed_search_decision.py:26`). Exceptions are stored on the instance (`tawreed_bot_core.py:64-65`) and re-raised via `bot.skip_item_exception(...)` — callers must know exception classes they never see. `tawreed_bot_methods.py` is 15+ pure delegation methods with an explicit "Delegation methods for backward compatibility with tests" comment — textbook shallow module.

**Deletion test:** delete `TawreedBotMethods` and the complexity vanishes (callers could call `bot.order_flow.X` directly). Delete the whole `bot` and its 30-attribute interface reappears across ~40 flow functions.

## Solution

Split the god object behind two small interfaces:

- A pure `MatchEngine` — `match(item, search_adapter) -> MatchOutcome` where `MatchOutcome` carries decision, queries, and timings, replacing the `last_*` write-back channel.
- A `RunControls` port — `should_stop()`, `skip(reason)`, `log()`.

The API/browser duality already present in `tawreed_bot_api._try_api_order / _try_api_match_only / _try_api_cart_removal` is the natural place for one `TawreedBackend` seam with two adapters: API client and browser flow.

## Before / After

### Before — one wide interface, 30 attributes, 40 callers

```
                 ┌───────────────────────────────────────────┐
                 │        TawreedBot  (interface)            │
                 │  config · selectors · profile_key · page  │
                 │  last_match_decision · last_queries       │
                 │  skip_item_exception · no_results_exc     │
                 │  _stop_before_item · _reset_last_item …   │
                 │  ~30 attributes (one for every concern)   │
                 └────────────┬──────────────────────────────┘
                              │ mutated in place
   ┌──────────────┐  ┌────────┴────────┐  ┌───────────────────┐
   │ api flow     │  │ matching       │  │ order             │
   │ (40 funcs)   │  │ (search_logic) │  │ (placement/summ)  │
   │  ↳ bot.x = … │  │  ↳ bot.x = …   │  │  ↳ bot.x = …      │
   └──────────────┘  └────────────────┘  └───────────────────┘
```

### After — two small ports, one deep implementation each

```
   ┌─────────────────────┐   ┌─────────────────────┐
   │   MatchEngine       │   │   RunControls       │
   │ match(item, search) │   │ should_stop()       │   ← interface
   │   → MatchOutcome    │   │ skip(reason)        │     (small)
   └──────────┬──────────┘   └──────────┬──────────┘
              │ deep implementation     │ deep implementation
              ▼                         ▼
   ┌─────────────────────┐   ┌─────────────────────┐
   │ scoring · cache ·   │   │ stop flag · log ·   │
   │ queries · decisions │   │ skip policies       │
   └─────────────────────┘   └─────────────────────┘
                                                 ╲
                                                  ╲  one TawreedBackend seam
                                                   ▼
                                       ┌─────────────────────┐
                                       │ TawreedBackend      │
                                       │   (interface)       │
                                       └──────────┬──────────┘
                                                  │
                            ┌─────────────────────┴────────────────────┐
                            ▼                                          ▼
                  ┌─────────────────────┐                  ┌─────────────────────┐
                  │ ApiAdapter          │                  │ BrowserAdapter      │
                  │  (tawreed_api.py)   │                  │  (Playwright page)  │
                  └─────────────────────┘                  └─────────────────────┘
```

## Wins

- interface shrinks from 30 attributes to 2 ports
- locality: bot-mutation bugs concentrate in one module
- tests stop faking 10-attribute `Mock` / `SimpleNamespace` bots
- leverage: one seam (`TawreedBackend`), two adapters
- ADR-worthy: the "bot is the world" pattern is the single most expensive assumption in `src/tawreed`
