# C6 — Collapse the manual-review wrapper layer

**Strength:** Worth exploring
**Tag:** in-process

## Files

- `src/core/manual_review/manual_review_helpers.py` (~370)
- `src/core/manual_review/manual_review_runtime.py` (165)
- `src/ui/manual_review/streamlit_manual_review_input.py` (103)
- `src/ui/manual_review/streamlit_manual_review_page.py` (235)

## Problem

`manual_review_runtime.should_skip_auto_save_verified_match` (`:136-153`) is a documented one-line pass-through of `manual_review_helpers.should_skip_auto_save` — a shallow module added only to give a "public wrapper" name. Every helper in `manual_review_helpers.py` is `_private`-named yet re-exported in `__all__` (`:350-368`, 18 names) — interface ≈ implementation; the "module" is a bag of functions. `_lookup_with_retry` creates `ManualReviewStore()` internally (a comment admits: "Default path is resolved at call time so tests can patch DEFAULT_MANUAL_REVIEW_DB") — a global-patching seam instead of injection.

`_manual_review_id_match` / `_find_name_match_in_candidates` hardcode score `999.0` and decision reason strings (C4's duplication source).

On the UI side, `streamlit_manual_review_input.py:40-79` (`_decision_from_row`, `_correction_fields`, `_manual_decision`, `_clean`) re-encodes the `ManualReviewDecision` row schema in the UI, while `core/manual_review/manual_review_selection.decision_from_selection` (imported by `streamlit_manual_review_page.py:10`) encodes it a second way for a different input shape — duplicated knowledge of the decision schema across core and UI.

## Solution

Make `ManualReviewRuntime` (or keep module-level functions) take the store as a parameter with one default; expose exactly three operations:

- `decision_for(item) -> MatchDecision | None`
- `queries_for(item, base) -> list[str]`
- `apply(item, results) -> MatchDecision | None`

Delete the `manual_review_runtime` wrapper. Move row → decision mapping into `core/manual_review` once (`decision_from_row`) and use it from both UI paths. The `999.0` fabrication moves behind the factory from C4.

## Before / After

### Before — mass diagram: interface as tall as implementation

```
  manual_review_helpers
  ┌─────────────────────────────────┐  ← interface (__all__: 18 names,
  │ should_skip_auto_save           │     many _private)
  │ _find_manual_review_match       │
  │ _manual_review_id_match         │
  │ _find_name_match_in_candidates  │
  │ _lookup_with_retry (global)     │
  │ _apply_saved_match …            │
  ├─────────────────────────────────┤
  │ row schema re-encoded           │  ← implementation
  │ 999.0 fabrication               │     (shallow: interface ≈ impl)
  └─────────────────────────────────┘

  manual_review_runtime  (pass-through, ~165 lines, 0 real behaviour)
```

### After — short interface, tall implementation

```
  ┌─────────────────────────────┐  ← interface (3 operations)
  │ decision_for(item)          │
  │ queries_for(item, base)     │
  │ apply(item, results)        │
  └──────────────┬──────────────┘
                 │ deep implementation
                 ▼
  ┌─────────────────────────────┐
  │ store (injected)            │
  │ row schema (one mapping)    │
  │ 999.0 fabrication           │
  │ retry / cache / diagnostics │
  └─────────────────────────────┘
        ▲
        │  used by both UI paths
        │
  decision_from_row (one helper, in core)
```

## Wins

- delete ~165 lines of pass-throughs
- one decision schema mapping
- store injectable: global-patching seam goes
- interface shrinks from 18 names to 3
- leverage: same `decision_for` works for CLI and UI flows
