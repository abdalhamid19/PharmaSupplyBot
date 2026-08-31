# Logging System

> **Status:** live — every Python module in `src/` uses the unified logger
> configured by `src.cli.logging_setup.configure_logging`. The numbers in
> `docs/audit_baseline.md` are all zeroes.

This document is the source of truth for how logging works in
PharmaSupplyBot. If the code disagrees with this document, the **code
wins** — please open a PR to update the docs.

---

## 1. Quick reference

| Flag | Effect |
|------|--------|
| `--log-level DEBUG` | More detail on console + files (default `INFO`). |
| `--quiet` / `-q` | Console: WARNING+ only. Files: unchanged. |
| `--json-logs` | Machine-readable output (one JSON record per line). |

| Stream | Content |
|--------|---------|
| `stderr` | Console (default `INFO`; `--quiet` raises it to `WARNING`). |
| `logs/app.log` | Everything DEBUG+ (rotates daily, 14 backups kept). |
| `logs/errors.log` | ERROR+ only (separate file for alerting). |

---

## 2. How logging is wired

The single init point is `configure_logging()` in
`src/cli/logging_setup.py`. It is called once at the top of
`run.main()`, **before** any subcommand runs:

```python
# src/cli/logging_setup.py
def configure_logging(config: LoggingConfig | None = None) -> None:
    cfg = config or LoggingConfig()
    root = logging.getLogger()
    root.setLevel(_resolve_level(cfg.level))
    # ... attach console + rotating file + rotating error file handlers
```

Everything that needs to emit a log line just calls
`logging.getLogger(__name__)` at module level and uses the resulting
`logger` from then on. No file outside `logging_setup.py` is allowed to
configure handlers — see § 5 for the policy and the CI guard tests that
enforce it.

---

## 3. How to add logging to a new module

```python
# foo/bar.py
import logging

logger = logging.getLogger(__name__)


def do_something(profile: str) -> None:
    logger.info("starting work", extra={"profile": profile})
    try:
        ...
    except SomeError:
        logger.exception("work failed for profile")
```

### 3.1 Which level to use

| Situation | Level |
|-----------|-------|
| Normal progress marker | `INFO` |
| Detail useful for diagnosis only | `DEBUG` |
| Recoverable unexpected event (e.g. session expired, retrying) | `WARNING` |
| One item / one operation failed (the rest can continue) | `ERROR` |
| Stack trace for a bug | `logger.exception(...)` inside `except` |
| Whole command cannot continue | propagate or `CRITICAL` (rare) |

### 3.2 Structured fields with `extra=`

Pass structured data via `extra={...}`. In `--json-logs` mode these
fields become first-class JSON keys; in human format they don't appear
but they're still searchable via `grep` on the file:

```python
logger.info(
    "matching started",
    extra={"profile": "wardany", "count": 42},
)
```

### 3.3 Multi-process / parallel work

`logging` is thread-safe and fork-safe in stdlib. Each worker should
call `logging.getLogger(__name__)` exactly once at module import time —
do **not** create per-process handlers; the parent's handlers still
apply because the subprocess inherits the root logger configuration.

---

## 4. Anti-patterns (rejected by CI)

These are *enforced* by `tests/core/test_logging_audit.py`. Adding any
of them will fail CI:

| Anti-pattern | Why it's wrong | What to do instead |
|--------------|----------------|--------------------|
| `print(...)` in `src/` | Loses level / timestamp / file output. | `logger.info/warning/error(...)`. |
| `logging.basicConfig(...)` outside `logging_setup.py` | `basicConfig` installs a root handler that *replaces* ours, so `logs/app.log` silently stops being written to. | Only `configure_logging()` configures handlers. |
| `logging.getLogger("some.literal.string")` (other than root) | Hand-picked names do not survive moves / refactors. | `logging.getLogger(__name__)`. |
| `logger.handlers = [...]` or `logger.addHandler(...)` outside `logging_setup.py` | The whole point of the unified setup is to own the handler chain. | Let the child logger inherit from root. |
| `_console_safe(...)` | Was a workaround for cp1252 Windows consoles. The unified logging handler writes UTF-8, so this is dead code. | `logger.info(...)` directly. |

The exception `logging.getLogger("src.core.drug_matching")` in
`src/core/drug_matching/config/config_helpers.py:setup_logging()` is
deliberate: it adjusts the matching package's effective level so every
matching submodule inherits the change.

---

## 5. Audit tool

Run the audit report at any time:

```bash
py scripts/audit_logging.py
```

It produces a markdown report at `docs/audit_logging.md` with the
headline numbers and per-file offender lists. Today every count is
zero:

| Category | Count |
|----------|------:|
| `print()` calls | 0 |
| `basicConfig()` calls | 0 |
| `"pharmasupplybot.matching"` literal loggers | 0 |
| `_console_safe()` calls | 0 |
| Manual handler manipulation | 0 |

Use this as a smoke test before opening a PR that touches logging.

---

## 6. Tests

| File | What it covers |
|------|----------------|
| `tests/cli/test_logging_setup.py` | Configure / idempotency / quiet / json / rotating handlers / public constants. |
| `tests/core/test_errors.py` | Exit codes 1–7 of every `PharmaSupplyError` subclass. |
| `tests/cli/test_registry.py` | `@register` decorator and the 5 production commands. |
| `tests/core/matching/test_logging_integration.py` | Matching submodules inherit from root; `setup_logging` adjusts the package level; the deprecated wrappers are no-ops. |
| `tests/core/test_logging_audit.py` | CI guards: no `print`, no `basicConfig`, no literal loggers, no `_console_safe`, no manual handlers, only allowed `getLogger` forms. |
| `tests/cli/test_run_logging_e2e.py` | `run.py` subprocess smoke for every command, plus `app.log` / `errors.log` invariants. |
| `tests/cli/test_logging_json_e2e.py` | `--json-logs` schema, required fields, no human-format leak. |
| `tests/cli/test_logging_quiet_e2e.py` | `--quiet` / `-q` / `--log-level DEBUG\|WARNING` behaviour. |

---

## 7. History

The system was built in stages. Each commit is a self-contained
checkpoint:

1. `bf11bac` — Stage 1: AST-based audit + 6 CI guard tests + baseline doc.
2. `6852c64`, `c69fd5f` — Stage 2: every `print()` and `_console_safe()`
   in `src/tawreed/` replaced with structured logger calls.
3. `280e733` — Matching-logging merger: `setup_logging` and
   `configure_async_logging` deprecated to no-op wrappers.
4. `4e59470` — Stage 4: 19 modules migrated from the literal
   `"pharmasupplybot.matching"` logger name to `getLogger(__name__)`.
5. Final stage — e2e CLI tests, full doc refresh.