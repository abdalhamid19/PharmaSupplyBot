# PharmaSupplyBot Project Guidelines

This document defines the project rules for `PharmaSupplyBot` and keeps them
aligned with the current repository structure, runtime model, and local audit
tooling.

## Purpose

- Keep the codebase maintainable while automating `seller.tawreed.io` flows.
- Improve execution speed, memory efficiency, and safe scalability.
- Keep the rules compatible with the current `src/`, Streamlit, and CLI layout.
- Distinguish between hard audit constraints and architectural guidance.

## Project Scope

- `run.py`: CLI entrypoint for auth, ordering, and cart removal.
- `streamlit_app.py`: local Streamlit entrypoint.
- `src/`: configuration, Excel loading, matching, Tawreed automation, and UI
  helpers.
- `input/`: source Excel files for orders, prevented items, and cart removal.
- `state/`: persisted Playwright session-state JSON files.
- `artifacts/`: run outputs, summaries, timing data, and diagnostic logs.

## Hard Constraints

These rules are enforced today by `python3 tools/rule_audit.py`.

- Target Python version: 3.10 or newer.
- Maximum line length: 100 characters.
- Public modules must have a module docstring.
- Public functions and classes must have docstrings.
- The audit currently flags files longer than 100 lines and functions longer
  than 20 lines, with a small exception list.

These file and function size thresholds are code-health guardrails, not
performance rules. Do not split logic into artificial fragments just to satisfy
a number if that would hurt clarity, cohesion, or runtime behavior.

## Style and API Rules

- Use `snake_case` for functions and variables, `PascalCase` for classes, and
  `UPPER_SNAKE_CASE` for constants.
- Prefer descriptive names over short abstractions such as `util`, `handler`,
  `data`, or `temp`.
- Use type hints on public APIs and shared domain models.
- Prefer precise types over `Any` where practical.
- Keep public interfaces small and stable.
- Avoid global mutable state; inject dependencies and pass explicit inputs.
- Write comments to explain intent, invariants, or tradeoffs, not obvious code.

## Architecture Rules

- Separate business logic from Playwright, CLI, and Streamlit integration code.
- Keep configuration loading separate from configuration consumption.
- Keep matching and warehouse-selection logic separate from browser actions.
- Prefer pure functions for parsing, matching, scoring, and validation.
- Reserve side effects for integration layers such as `tawreed*.py`,
  `streamlit_*.py`, and CLI command wiring.
- Add new behavior as explicit services, commands, or strategies instead of
  growing monolithic control flows.
- Avoid import cycles and keep dependencies moving inward toward reusable logic.

## Import Rules

- Inside `src/`, prefer package-relative imports such as `from .excel import Item`
  because that matches the current codebase.
- In top-level entrypoints and tests, import through `src...` when needed.
- Avoid cross-module imports that pull UI code into domain or runtime modules.

## Performance Rules

### General

- Measure before optimizing; use timing data or lightweight profiling on slow
  paths before making structural changes.
- Optimize repeated work first: redundant Excel reads, repeated DOM scans,
  duplicate parsing, unnecessary retries, and repeated browser/session setup.
- Prefer algorithmic improvements over micro-optimizations.
- Treat every new loop over items, rows, or products as a potential hot path.

### Memory

- Do not keep large intermediate collections unless later steps reuse them.
- Prefer iterators, generators, and incremental writes for one-pass workflows.
- Avoid copying lists, dicts, or DataFrames unless isolation is required.
- Keep caches bounded by size or lifetime; unbounded caches are forbidden.
- Keep temporary state local to one run instead of storing long-lived mutable
  process state.

### Excel and Data Loading

- Read only the columns needed for the current operation.
- For large spreadsheets, prefer chunked or streaming approaches when library
  support is practical.
- If `pandas` remains in use, avoid loading full sheets twice when one preview
  pass and one targeted read are sufficient.
- Prefer row iteration APIs that avoid Series allocation per row when converting
  Excel rows into domain objects.
- Normalize and validate rows as they are read instead of building multiple
  transformed copies of the same dataset.

### Playwright and Network Use

- Reuse one browser/context/page sequence for a single run whenever possible.
- Reuse validated session-state files to avoid unnecessary reauthentication.
- Prefer waiting on precise UI signals over broad sleeps or repeated polling.
- Avoid repeated DOM queries for the same stable element inside tight loops.
- Bound retries and timeouts explicitly; no unbounded waiting loops.
- Close dialogs, pages, contexts, and files deterministically.

### Concurrency and Throughput

- Parallelism must be bounded. Do not run unlimited profiles, browsers, or file
  loads at once.
- If multi-profile execution is added or expanded, control concurrency with a
  fixed worker limit or semaphore.
- Shared output files must be append-safe or partitioned per run/profile.
- Any cache or session reuse must be safe across concurrent runs.

## Scalability Rules

- Make expensive behavior configurable through `config.yaml` or typed config
  models, not hardcoded constants.
- Define explicit extension points for auth flows, warehouse strategies, and
  input-source handling.
- Prefer structured result objects over ad hoc dictionaries when values cross
  multiple layers.
- Keep per-profile execution isolated so failures in one profile do not corrupt
  another.
- Persist artifacts incrementally instead of holding full run history in memory.
- Prefer append-only logs and summaries for long runs.

## Project Organization

- Keep `src/` modules focused on one clear responsibility each.
- `config.py`, `config_factory.py`, and `config_models.py` own configuration.
- `excel.py`, `prevented_items.py`, and related helpers own input processing.
- `matching_*.py`, `product_matching.py`, and `tawreed_strategy.py` own match
  and selection logic.
- `tawreed*.py` own browser automation, session validation, and order/cart flow.
- `streamlit_*.py` own presentation and subprocess orchestration only.
- Keep `input/`, `state/`, and `artifacts/` outside source logic concerns.

## Refactoring Rules

- Do not change business behavior during refactoring unless the task explicitly
  includes a behavior change.
- Extract helpers or modules when they improve cohesion, testability, or
  performance visibility.
- Do not split a function only to satisfy a size target if the result increases
  call indirection without improving readability.
- If a file exceeds audit thresholds, reduce it deliberately around logical
  seams rather than by mechanical slicing.
- Preserve existing public interfaces unless the migration is planned and tested.

## Testing and Validation

- Run `python3 tools/rule_audit.py` after structural changes.
- Add or update tests when changing matching, parsing, session, or orchestration
  logic.
- Prefer focused unit tests for scoring, parsing, and selection logic.
- For performance-sensitive code, add regression-friendly checks when practical,
  such as row-count, timeout, or bounded-work assertions.

## Project-Specific Guidance

- Keep `order_items`, `prevented_items`, and `remove_items` flows explicit and
  separate.
- Do not duplicate product-matching rules inside browser-flow modules when the
  logic can live in shared matching modules.
- Store persistent auth state only in `state/`; `artifacts/` must remain
  disposable run output.
- When adding warehouse-selection behavior, prefer extending
  `tawreed_strategy.py` or related matching logic instead of branching in UI or
  CLI layers.
- If configuration models grow, prefer typed fields and smaller nested models
  over broad `dict[str, Any]` surfaces.

## Source of Truth

- `docs/project_guidelines.md` is the main project rule document.
- `tools/rule_audit.py` is the source of truth for currently enforced local
  audit checks.
- When these two disagree, either update the document or update the audit so
  both describe the same expectation.
