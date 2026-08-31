# Architecture Review — PharmaSupplyBot

**Date:** 2026-08-30
**Scope:** `src/` (Python; Typer CLI, Streamlit UI, browser/API layer, pure domain logic)
**Method:** `improve-codebase-architecture` skill — surface deepening opportunities (small interface, large implementation, clean seam) using the `/codebase-design` vocabulary (module, interface, implementation, depth, deep, shallow, seam, adapter, leverage, locality).
**Inputs:** recent git history (logging-system merge + ai-config stages, api-flow refactors, swallowed-exception audit), the top hot-spot files, and import-direction grep across `src/`.

The report is split into one file per candidate plus this index. The visual HTML companion is at the temp path printed by the agent (`%TEMP%\architecture-review-*.html`).

## Positive calibration

`src/core/matching/product_matching.explain_best_product_match` is already a deep module done right — three parameters hide ~1,800 lines of scoring/acceptance, and 20+ tests hit the interface directly without reaching for private helpers. Most of the friction below lives in the *layer around* it (tawreed flows, bot state, artifacts, UI command building), not inside the core matcher.

## Dependency direction (verified by grep)

| Package | Imports | Verdict |
|---|---|---|
| `src/core` | only `src.core` | Clean. Zero imports of `tawreed` / `cli` / `ui`. |
| `src/tawreed` | `src.core` + sibling `tawreed.*` subpackages | Downward, very wide (see C1, C3). |
| `src/cli` | `src.core`, `src.tawreed` (incl. 3-level-deep paths) | Downward, acceptable but reaches far into tawreed internals. |
| `src/ui` | `src.core` only | Zero direct imports of `src/tawreed`; the UI reaches tawreed only by spawning `run.py` subprocesses. |

Import-cycle and leakage notes:

- **Package-level cycle** `core.matching ↔ core.manual_review`, patched with deferred imports (`core/manual_review/manual_review_candidates.py:8`, `core/manual_review/manual_review_helpers.py:91,137,209,297`, `core/matching/matching_risk.py:40`).
- **Bidirectional package dependency** between `core.matching` and `core.identity` (top-level imports both ways; no module-level cycle).
- **Cycle-avoidance scar tissue** in `src/tawreed/api/`: 52 function-level imports, 20 of them in `tawreed_api_flow_matching.py` alone.
- **Private-name leakage** across package boundaries: `tawreed_api_flow_matching.py:20` and `tawreed/matching/tawreed_search_logic.py:18` import `_search_queries_for_item`; `tawreed_api_contract_discovery.py:19` imports `_search_response_pattern`; `tawreed/api/__init__.py:96-98` re-exports `_api_origin`, `_is_trusted_add_to_cart_url`, `_auth_headers_from_state` in `__all__`.
- No upward imports anywhere.

## Candidates

| # | Candidate | Strength | File |
|---|-----------|----------|------|
| 1 | Give `TawreedBot` two small interfaces | Strong | [C1_tawreed_bot_god_object.md](C1_tawreed_bot_god_object.md) |
| 2 | Delete the duplicate API match flow | Strong | [C2_delete_duplicate_api_match_flow.md](C2_delete_duplicate_api_match_flow.md) |
| 3 | One match loop, two search adapters | Strong | [C3_unify_match_loop.md](C3_unify_match_loop.md) |
| 4 | Type the decision source | Strong | [C4_typed_decision_source.md](C4_typed_decision_source.md) |
| 5 | One `RunSpec`, one `RunMonitor` for the UI | Strong | [C5_runspec_runmonitor.md](C5_runspec_runmonitor.md) |
| 6 | Collapse the manual-review wrapper layer | Worth exploring | [C6_collapse_manual_review_wrappers.md](C6_collapse_manual_review_wrappers.md) |
| 7 | One config surface | Strong (partial) | [C7_one_config_surface.md](C7_one_config_surface.md) |
| 8 | Read artifacts through one interface | Worth exploring | [C8_run_artifact_store.md](C8_run_artifact_store.md) |

## Top recommendation

**C2 — delete the duplicate API match flow.** Lowest-risk deepening in the set: a near-dead 150-line copy of `tawreed_api_flow_matching.py`, a facade that re-exports ten `_private` names, and a public entry point whose interface requires a fake bot with ≥6 attributes. Deleting the copy, shrinking the facade, and parameterising `require_api_match(item, search, policy)` exposes the seam that C3 needs and lets the test that currently imports `_require_orderable_api_match` hit the public interface instead. Small interface, large implementation, clean seam — the whole point of the exercise.
