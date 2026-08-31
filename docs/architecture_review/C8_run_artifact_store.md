# C8 — Read artifacts through one interface

**Strength:** Worth exploring
**Tag:** local-substitutable

## Files

- `src/core/artifact_run.py` (100 — the good deep-ish module for the *write* side's neighbours)
- `src/tawreed/artifacts/tawreed_artifacts_io.py` (214) + `tawreed_artifacts.py` (183)
- `src/tawreed/artifacts/order_result_merger.py` (96)
- `src/cli/commands/cli_order_items.py:55-67` (`latest_summary_path`, knows 4 layouts)
- `src/cli/commands/cli_order.py:132-186` (`_newest_run_dirs`, `_count_from_summary_csvs` — the CLI *re-reads its own just-written CSVs* to compute the command summary)
- UI paths (see C5)

## Problem

`tawreed_artifacts.py` is genuinely deep for *writing* (`append_csv_artifact(profile, label, rows)` handles run-scoping, schema evolution, XLSX) — but *reading* the same artifacts has no interface:

- `cli_order_items.latest_summary_path` hardcodes 4 layouts (active run, `artifacts/order/<p>/*`, `artifacts/<p>` legacy, `artifacts/legacy/<p>/*`).
- `cli_order._newest_run_dirs` re-derives newest-run by mtime.
- UI globs again (C5).
- `manual_review` page finds run dirs with its own `_available_runs_with_candidates` glob (`streamlit_manual_review_page.py:54`).

`write_match_log` (`tawreed/matching/tawreed_match_logs.py:54-66`) writes three artifact files per item from deep inside matching logic — matching and artifact layout are tangled; every match test must therefore tolerate file writes or patch `write_text_artifact`.

**Test-seam evidence:** `tests/tawreed/api/test_empty_store_product_id_guard.py:12,86` imports the *private* functions `_require_orderable_api_match` and `_is_saved_manual_review_match` — because the public `require_api_match(bot, api, item, ...)` requires a fake bot with ≥6 attributes. `tests/test_item_worker_execution.py:6-9` and others use `SimpleNamespace` / `Mock` bots with the same scaffolding.

## Solution

Extend `core.artifact_run` into a `RunArtifactStore`:

- `latest(command, profile, label) -> Path | None` (one definition of "the most recent summary"; absorbs `latest_summary_path`)
- `rows(label) -> list[dict]`
- `append(label, rows)` (delegating to `tawreed_artifacts`)
- `count_statuses(label) -> dict` (absorbing `cli_order._count_from_summary_csvs`)

Delete the four glob re-implementations. Give `write_match_log` an observer / collector injected by the flow so matching stays pure and tests stop patching `write_text_artifact`.

## Before / After

### Before — one writer, four readers, four different glob strategies

```
  ┌──────────────────────────────┐
  │ tawreed_artifacts.py         │
  │ append_csv_artifact(...)     │  ← deep write side
  │ write_text_artifact(...)     │
  └──────────────────────────────┘
            │ writes
            ▼
       artifacts/order/<p>/<run>/...
       artifacts/<p>/<run>/...         (legacy)
       artifacts/legacy/<p>/<run>/...  (legacy)
            ▲ reads (each guesses)
   ┌────────┴────────┐
   │ cli_order_items│   cli_order
   │  latest_summary│   _newest_run_dirs
   │  (4 layouts)   │   _count_from_summary_csvs
   └────────────────┘   (re-reads just-written CSVs)
   ┌──────── streamlit_manual_review_page._available_runs_with_candidates (own glob)
   ┌──────── streamlit_order_form._latest_order_summary_path (own glob)
   ┌──────── streamlit_shared.summary_csv_path (legacy flat)
   ┌──────── tawreed_match_logs.write_match_log (writes 3 files from inside matching)
```

### After — one store, all reads go through it, matching stays pure

```
  ┌──────────────────────────────┐
  │ RunArtifactStore (interface) │
  │ latest(cmd, profile, label)  │
  │ rows(label)                  │
  │ append(label, rows)          │
  │ count_statuses(label)        │
  └──────────────┬───────────────┘
                 │ deep implementation (writes + reads)
                 ▼
  ┌──────────────────────────────┐
  │ tawreed_artifacts (write)    │
  │ path layout (one source)     │
  │ legacy / active / order run  │
  └──────────────────────────────┘
        ▲
        │ uses
   CLI / UI / matching
        │
   matching → MatchObserver (injected), not write_match_log
```

## Wins

- one implementation for read + write
- legacy-layout guessing deleted
- locality: layout changes touch one module
- match tests stop tolerating file writes
- leverage: every consumer (CLI, UI, matching) reads through the same interface
- pair with C5: `RunSpec` and `RunArtifactStore` together close the UI/CLI seam end-to-end
