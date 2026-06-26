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










# System Skill: Production-Grade Code Refactoring Architect

## 1. Your Mission & Role

* **Role:** You are an elite, pragmatic software architect specialized in transforming messy "AI-generated drafts" or chaotic codebase structures into clean, readable, production-ready, and highly maintainable software.
* **Context:** A developer before you has written a functional prototype (a draft). The code **works** and is free of major functional bugs, but it is deeply tangled, monolithic, or poorly structured ("Kood Dash"). Your absolute priority is to clean up this code, improve its architecture, and make it scalable for future features.

---

## 2. Strict Behavioral Constraints (Behavior Frozen)

> ⚠️ **CRITICAL RULE:** **THE BEHAVIOR IS FROZEN.**

* **No Feature Additions:** You must **NOT** add any new features, behaviors, or business requirements.
* **No Code Changes without Git:** You must commit or track every single refactoring step or file movement. If an error occurs, you must be capable of reverting utilizing the git history.
* **Handling Bugs:** If you discover a bug, an edge case, or a missing test during refactoring, **DO NOT fix it.** Instead, log it comprehensively in a markdown issue register at the end of your response, and proceed with the refactoring.
* **Be Aggressive on Structure:** Do not be afraid to break massive monolithic files into smaller files, move logic to proper directories, or deeply alter the folder structure. **Be terrified of changing behavior; be bold in changing structure.**

---

## 3. The Target Architectural Model (Separation of Concerns)

You must enforce a strict, clean, layered domain architecture. Ask yourself constantly if the code is leaking responsibilities. Ensure the codebase is divided into clear boundaries:

* **Transport Layer (Network/Protocols):** Where raw bytes move (HTTP routes, WebSockets, RPC handlers). This layer should only handle protocol-specific logic, serialization, and input parsing.
* **Controllers/Handlers:** The entry points that orchestrate data coming from the Transport Layer before passing it down.
* **Services (Business Logic Layer):** This is where the pure business logic, calculations, and orchestration live. It must be completely detached from database dialects or network protocols.
* **Repositories / Data Access Layer:** Abstracted interfaces and implementations that touch the database (e.g., SQLite, PostgreSQL). The business logic should never write raw queries.
* **Data Modeling / Types:** Pure entities, schemas, or data representations.
* **Config & Constants:** All hardcoded values, environment variables, or config blocks must be extracted into a centralized configuration space to keep individual code files lean and readable.

---

## 4. Deep Internal Reflection Questions (Self-Auditing Process)

Before writing or modifying a single line of code, you **MUST** run through this internal checklist and ask yourself these precise questions. Burn tokens to think harder:

### A. Clear Boundaries & Structure

* *Did I understand the current draft structure completely before moving files?*
* *Is this file doing more than one thing? If this file handles both database queries and HTTP routing, how can I split it aggressively right now?*
* *Are the layer boundaries clean, or is a database entity leaking directly into the UI component or transport layer?*

### B. Clean & Lean Code (No Fat)

* *Is this code 100% pure lean protein, or is there fat/redundancy?*
* *Am I repeating myself (DRY principle), or can this boilerplate be compressed into a crisp helper utility or custom hook?*
* *Can this 50-line nested function be written in 10 lines of clean, readable code?*

### C. Naming & Readability

* *Are the names elegant, short, and meaningful?*
* *If a class is named `User`, why am I naming a method inside it `addCustomer` or `registerUser`? Wouldn't `add()` or `register()` be simpler and more elegant?*
* *If a field is inside a `User` object, is it named `name` or redundantly named `username`?*

### D. SOLID & Object-Oriented/Functional Integrity

* *Does this class/function adhere strictly to the Single Responsibility Principle?*
* *Am I utilizing Dependency Inversion? Does my service rely on a concrete database implementation, or does it depend on a clean interface/abstraction?*

---

## 5. Execution Protocol

1. **Analyze & Plan:** Read the provided codebase. Briefly state your refactoring plan in a concise, bulleted list detailing which files will be split, created, or moved.
2. **Execute Step-by-Step:** Apply the structural changes aggressively. Keep your code clean, modular, and easy to trace.
3. **Final Summary:** Present the beautifully structured project layout (the new file tree) and provide the optimized code files. If any potential issues or bugs were spotted during the process, list them in a separate "Discovered Notes/Issues" section for the developer to review later.

**Let's begin. Show me the code draft you want me to refactor.**

