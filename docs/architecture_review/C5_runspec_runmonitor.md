# C5 — One `RunSpec`, one `RunMonitor` for the UI

**Strength:** Strong
**Tag:** local-substitutable

## Files

- `src/ui/order/streamlit_order_command.py` (127)
- `src/ui/order/streamlit_order_process.py` (218)
- `src/ui/streamlit_remove_cart.py` (284)
- `src/ui/manual_review/streamlit_manual_review_cli.py` (159)
- `src/ui/views/streamlit_process.py` (134)
- `src/ui/streamlit_shared.py` (93)
- `src/core/artifact_run.py` (100 — already deep-ish, but only the write side is used)

## Problem

The UI goes through CLI subprocesses (the seam exists): `streamlit_process.run_cli_subprocess` / `start_cli_subprocess` spawn `[sys.executable, run.py, *argv]`, and UI tests monkeypatch exactly that seam. But the argv itself is hand-assembled string lists in three places — `order_command()` (`order_command.py:13-27`), `remove_cart_command()` (`remove_cart.py:96-147`), `manual_review_remove_command()` / `corrected_review_search_command()` (`manual_review_cli.py:40-50, 78-84`). Each duplicates CLI flag spelling (`--execution-mode`, `--matching-risk-policy`, `--item-workers`, `--prevented-items-excel`, …). The CLI's argparse surface is a leaky interface the UI must know.

The running-process lifecycle is implemented three times with the same shape (poll → stop-flag write → output read → close handle → render result → `st.session_state.pop`): `streamlit_order_process.py:23-83`, `streamlit_remove_cart.py:274-328`, `streamlit_manual_review_cli.py:87-136`. Helper bodies are identical: `order_process_output` ≡ `remove_cart_process_output` ≡ `_read_output_file`; `close_order_process_output` ≡ `close_remove_cart_process_output`.

**Path drift has already happened**: `run_control` vs `run-control`. `streamlit_remove_cart.py:183,190` and `streamlit_manual_review_cli.py:55,141` use `ARTIFACTS_DIR / "run_control"`, while `streamlit_order_form.py:59` uses `ARTIFACTS_DIR / "run-control" / "order"`, and `core/artifact_run.py:64` defines `run_control_dir()` (unused by the UI). Two spellings of the same directory in the same package.

Hardcoded profile `"wardany"` as fallback in 5 UI files (`streamlit_shared.py:76,78`, `streamlit_order_form.py:110,116`, `streamlit_remove_cart.py:333`, `views/streamlit_overview.py:24`), plus `Path("state/config.yaml")` hardcoded in `streamlit_manual_review_cli.py:21,72` instead of using `streamlit_shared.DEFAULT_CONFIG_PATH`.

Summary-path discovery duplicated: `streamlit_order_form._latest_order_summary_path` (glob `artifacts/order/<profile>/*/<label>_*.csv`) re-implements `src/cli/commands/cli_order_items.latest_summary_path` (which knows 4 layouts including legacy), and `streamlit_shared.summary_csv_path` still points at the *legacy flat* layout — so the UI's "watch the summary" feature silently disagrees with the CLI's own resume logic about where rows live.

## Solution

Two small modules in `src/cli` (it owns the flags):

- **`RunSpec`** — a typed dataclass of options, with `RunSpec.to_argv() -> list[str]` (single source of flag names, testable without streamlit).
- **`RunMonitor(status) -> RunStatus`** — encapsulates poll / stop / output / cleanup; takes a `RunSpec` and a `StartFn` (defaults to `start_cli_subprocess`).

UI modules shrink to form rendering + `st.*` calls. All paths come from `core.artifact_run`; delete the `run_control` spelling drift; the `wardany` fallback becomes a single constant in `streamlit_shared`.

## Before / After

### Before — three UI layers each carrying their own argv + lifecycle + paths

```
  ┌──────────── order UI ─────────────┐
  │ argv: --execution-mode, --profile │
  │ lifecycle: poll / stop / read     │  ~200 lines
  │ paths: hardcoded + run-control    │
  └───────────────────────────────────┘
  ┌─────────── remove-cart UI ────────┐
  │ argv: --execution-mode, --profile │  ~200 lines
  │ lifecycle: same code              │  duplicated
  │ paths: hardcoded + run_control    │  drift
  └───────────────────────────────────┘
  ┌────────── manual-review UI ───────┐
  │ argv: --matching-risk-policy …    │  ~150 lines
  │ lifecycle: same code              │  duplicated
  │ paths: hardcoded config.yaml      │  drift
  └───────────────────────────────────┘
```

### After — UI renders, `RunSpec` builds argv, `RunMonitor` owns lifecycle

```
  ┌─────── UI (thin) ───────┐
  │ form → st.button(…)    │
  │ st.session_state       │
  │ render output          │
  └──────────┬─────────────┘
             │ uses
             ▼
  ┌────── RunSpec ──────┐   ┌────── RunMonitor ──────┐
  │ to_argv()           │   │ poll · stop · output  │  ← deep impl
  │ single flag list    │   │ cleanup · status      │     (~100 lines,
  │ testable w/o streamlit   │ testable w/o streamlit  shared once)
  └──────────┬──────────┘   └──────────┬────────────┘
             │                          │
             └──────────┬───────────────┘
                        ▼
              core.artifact_run.RunArtifactStore  (C8)
```

## Wins

- CLI flag names live in one module
- three lifecycle copies collapse into one
- locality: path fixes happen once
- UI shrinks to rendering
- tests stop monkeypatching three different argv builders
- leverage: `RunSpec` is reusable by the CLI itself (e.g. for orchestrated batch runs)
