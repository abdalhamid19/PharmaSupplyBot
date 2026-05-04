# PharmaSupplyBot Project Guidelines

This document consolidates the project rules into a single file and aligns them
with the current structure of `PharmaSupplyBot`.

## Purpose

- Guide code development so it remains clear, maintainable, and suitable for
  automating `seller.tawreed.io` orders.
- Support the current project structure in `src/`, the Streamlit interface, and
  the `config.yaml` configuration files.
- Establish fixed rules for local code checks using `tools/rule_audit.py`.

## Project Scope

- `run.py`: The main command-line interface for auth, ordering, and cart removal.
- `streamlit_app.py`: The local Streamlit entrypoint.
- `src/`: Source code for configuration, matching, Tawreed automation, and UI logic.
- `input/`: Input Excel files, including `order_items/`, `prevented_items/`, and
  `remove_items/`.
- `state/`: Stored Playwright sessions for each profile.
- `artifacts/`: Diagnostic output and logs for failures.

## Core Code Rules

### Python Formatting

- Use Python 3.10 or newer.
- Use 4 spaces for indentation.
- Maximum line length: 100 characters.
- Do not use tabs.
- Use comments to explain why, not what.

### Code Length Rules

- Maximum file length: 100 lines.
- Maximum function length: 20 lines.
- If a file or function exceeds the limit, split the code into a separate module
  or helper function.

### Naming and Style

- Variables and functions: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Use fully descriptive names; do not abbreviate domain concepts.
- Avoid generic names like `data`, `temp`, `util`, or `handler` without clear
  context.

### Documentation

- Every public source file must have a module docstring.
- Every public function or class must have a clear docstring.
- Private helper functions should be prefixed with `_` and may include a short
  comment when needed.

### Performance and Memory Usage

- Minimize loading Excel files or page data into memory all at once.
- Use streaming or batch processing for large item lists.
- Avoid unnecessary data copies during processing; pass by reference when safe.
- Prefer operations on series or iterators over copying full DataFrames if using
  `pandas` or equivalent.
- Use temporary caches only for reusable outputs between requests, and avoid
  holding long-lived state.
- Keep temporary state localized to a single function or module to prevent
  memory leaks across broader scopes.
- Use indexing and smart lookup strategies instead of repeated scans over lists.
- Reduce repeated network or browser calls by reusing stored sessions and valid
  state when possible.
- Evaluate execution time and complexity when adding new features; make heavy
  features configurable.

## Scalability and Extensibility

- Design functions to be reusable across different execution flows, separate
  from UI details.
- Add new logic in separate modules instead of modifying large existing files.
- Use simple design patterns such as `Factory` or `Strategy` when adding new
  behavior without changing existing code.
- Keep clear extension points in the code so new flows can be added for
  `order`, `remove-cart`, `auth`, and similar commands without excessive
  coupling.
- Make configurable behavior driven by `config.yaml` rather than hardcoded
  constants inside functions.
- Consider a single extensibility layer (`extension` or `plugin`) for adding new
  input formats or authentication methods.

## Project Organization and Layering

- Keep `src/` code focused on well-defined responsibilities.
- `config.py`, `config_factory.py`, and `config_models.py` handle configuration
  loading and representation.
- `excel.py` and `selectors.py` handle input data and page element access.
- `product_matching.py`, `matching_models.py`, and `matching_rules.py` handle only
  item matching.
- `tawreed*.py` handle interaction with the Tawreed site and browser navigation.
- `streamlit_*.py` handle UI and presentation, clearly separated from runtime
  logic.

### Imports

- Use absolute imports within `src/` whenever possible.
- Keep `from src...` imports in Streamlit modules to avoid dynamic loading issues.
- Avoid heavy relative path dependencies between large `src/` modules.

### File and Folder Organization

- Use separate folders for each layer or responsibility in `src/`, such as
  `src/tawreed/`, `src/config/`, and `src/streamlit/` when appropriate.
- Place core business modules in one folder, configuration modules in another,
  and UI modules in a third.
- Ensure filenames reflect precise responsibility: `config_factory.py` for
  configuration loading, `product_matching.py` for matching, and
  `tawreed_checkout.py` for checkout flow.
- Combine files with shared responsibility only after confirming the merge does
  not exceed length limits or blur architectural layers.
- Keep `input/`, `state/`, and `artifacts/` separate from source code; use them as
  data and state directories only.
- If a file contains more than one responsibility, split it into a new subfolder
  rather than enlarging a single file.

## Review and Refactoring Rules

### General Rules

- Do not change program behavior during refactoring.
- Do not change business logic or algorithms unless explicitly requested.
- Do not delete working code; if a section is unused, document it in the review
  first.
- Give every new module exactly one clear responsibility.

### Module and Helper Extraction

- Extract a new module only when:
  - the file exceeds 100 lines, or
  - the file contains a distinct separate responsibility.
- Extract a helper function only if it improves readability or enables reuse.
- Keep private helper functions prefixed with `_` and place them after public
  functions in the file.

### Dependencies

- Keep dependencies pointing downward; higher-level modules should not depend on
  lower-level modules.
- Avoid import cycles.
- Prefer dependency injection over importing whole modules for general behavior.

### Separation of Concerns

- Separate UI logic from runtime and Tawreed automation logic.
- Separate configuration loading from configuration usage.
- Separate input validation from execution logic.

## Streamlit and Playwright Rules

- Keep UI logic inside `streamlit_*.py` and expose simple interfaces for business
  functions.
- Keep auth and stored session state separate in `streamlit_auth.py` and
  `streamlit_state.py`.
- Store Playwright sessions in `state/<profile>.json` and protect them from
  accidental overwrites.
- Use absolute imports like `from src...` when a Streamlit page needs to import
  a module.

## Local Validation

- Use `python3 tools/rule_audit.py` to verify length and documentation rules.
- Even if values appear in `EXCEPTED_FILE_LENGTHS`, reduce file sizes gradually
  during refactoring.
- Record audit results in the output and ensure there are no
  `rule_audit_violations` before merging.

## Project-Specific Notes

- Keep handling of `order_items`, `prevented_items`, and `remove_items` clear and
  separated.
- `artifacts/` should contain only run results and failure logs, not persistent
  runtime state.
- Avoid duplicating product matching logic inside `tawreed_*`; if logic can be
  shared, place it in `product_matching.py` or `matching_rules.py`.
- Keep tunable settings in `config.yaml` instead of hardcoding them in code.

## Desired Final Structure

- One consolidated rule file: `docs/project_guidelines.md`
- No nested separate rule files under `.agent/rules/refactoring/`.
- Content should focus on the current project and comply with the constraints
  defined in `tools/rule_audit.py`.
