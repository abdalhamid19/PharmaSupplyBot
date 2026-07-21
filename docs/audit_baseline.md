# Logging Audit — Final State

> Generated: 2026-07-21, branch `logging_system`
> Tool: `scripts/audit_logging.py`
> Reproduce: `py scripts/audit_logging.py`

This document captures the **final state** of logging usage in the
project after the unification plan completed. Every headline number
is zero — see `docs/logging_system.md` for the policy that keeps it
that way.

## Final headline numbers

| Category | Count |
|----------|------:|
| `print()` calls in `src/`               |    0 |
| `basicConfig()` calls in `src/`         |    0 |
| `"pharmasupplybot.matching"` literals   |    0 |
| `_console_safe()` calls                 |    0 |
| Manual handler manipulation             |    0 |
| `logging.getLogger()` callers (total)   |   46 |
| Files using `__name__` convention       |   27 |

Baseline vs. final, for reference:

| Metric                                    | Baseline | Final |
|-------------------------------------------|---------:|------:|
| `print()` in `src/`                        |       27 |     0 |
| `basicConfig()` calls                      |        0 |     0 |
| `"pharmasupplybot.matching"` literals      |       20 |     0 |
| `_console_safe()` calls                    |        4 |     0 |
| Manual handler manipulation               |        1 |     0 |
| Files using `__name__` convention         |       10 |    27 |

## Commits that produced this state

| Commit    | Title |
|-----------|-------|
| `bf11bac` | Stage 1: AST-based audit + 6 CI guard tests + baseline doc. |
| `6852c64` | Stage 2: every `print()` and `_console_safe()` in `src/tawreed/` replaced with structured logger calls. |
| `c69fd5f` | Cleanup of stale `_console_safe` comment in `tawreed_summary.py`. |
| `280e733` | Matching-logging merger: `setup_logging` and `configure_async_logging` deprecated to no-op wrappers. |
| `4e59470` | Stage 4: 19 modules migrated from the literal `"pharmasupplybot.matching"` logger name to `getLogger(__name__)`. |

## CI guards

`tests/core/test_logging_audit.py` enforces every rule above. If a
future commit introduces any of the anti-patterns (a `print`, a
`basicConfig`, a hand-picked logger name, manual handler manipulation,
or `_console_safe`), the guard test fails the build.

A full pytest run on the logging suites finishes in under five seconds:

```
tests/cli/test_logging_setup.py               14 passed
tests/core/test_errors.py                     13 passed
tests/cli/test_registry.py                     5 passed
tests/core/matching/test_logging_integration.py  12 passed
tests/core/test_logging_audit.py               9 passed
tests/cli/test_run_logging_e2e.py             10 passed
tests/cli/test_logging_json_e2e.py             8 passed
tests/cli/test_logging_quiet_e2e.py            9 passed
```