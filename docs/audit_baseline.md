# Logging Audit Baseline — Stage 1

> Generated: 2026-07-21, branch `logging_system`
> Tool: `scripts/audit_logging.py`
> Reproduce: `py scripts/audit_logging.py`

This document captures the state of logging usage across the project
*before* the unification work begins. Subsequent stages will be measured
against these numbers.

## Headline numbers

| Category                                | Count | Goal |
|-----------------------------------------|------:|-----:|
| `print()` calls in `src/`               |    27 |    0 |
| `basicConfig()` calls in `src/`         |     0 |    0 |
| `"pharmasupplybot.matching"` literals   |    20 |    0 |
| `_console_safe()` calls                 |     4 |    0 |
| Manual handler manipulation             |     1 |    0 |
| `logging.getLogger()` callers (total)   |    32 |   32 |
| Files using `__name__` convention       |    10 |   30 |

## Detailed breakdown

### `print()` calls (27) — all in `src/tawreed/`

| File | Count |
|------|------:|
| `src/tawreed/auth/tawreed_session_auth.py`           | 4 |
| `src/tawreed/api/tawreed_api_flow_cart.py`           | 3 |
| `src/tawreed/order/tawreed_order_summary.py`         | 3 |
| `src/tawreed/api/tawreed_api_contract_discovery.py`  | 2 |
| `src/tawreed/api/tawreed_api_discovery_enhanced.py`  | 2 |
| `src/tawreed/artifacts/tawreed_artifacts.py`         | 2 |
| `src/tawreed/order/tawreed_order_match.py`           | 2 |
| `src/tawreed/order/tawreed_order_placement.py`       | 2 |
| `src/tawreed/tawreed_auto_auth.py`                   | 2 |
| `src/tawreed/auth/tawreed_headless_auth_refresh.py`  | 1 |
| `src/tawreed/auth/tawreed_session_state.py`          | 1 |
| `src/tawreed/cart/tawreed_cart_removal.py`           | 1 |
| `src/tawreed/tawreed_bot_core.py`                    | 1 |
| `src/tawreed/tawreed_bot_methods.py`                 | 1 |

Note: `src/ui/order/streamlit_order.py:108,155` matches grep but those
are a function *name* `order_submission_fingerprint`, not actual `print()`
calls. AST-based audit correctly excludes them.

### `"pharmasupplybot.matching"` literal loggers (20)

These were the legacy convention before stage 2/3. They live in
`src/core/drug_matching/`, `src/core/matching/`, and one call in
`src/cli/commands/cli_match_products.py`. Stage 3 will replace each one
with `__name__`.

Files:
* `src/core/drug_matching/ai/ai_review.py`
* `src/core/drug_matching/ai/ai_review_execution.py`
* `src/core/drug_matching/ai/ai_search.py`
* `src/core/drug_matching/ai/ai_search_core_batch.py`
* `src/core/drug_matching/ai/ai_search_core_logging.py`
* `src/core/drug_matching/ai/ai_steps.py`
* `src/core/drug_matching/ai/ai_verify_batch.py`
* `src/core/drug_matching/ai/ai_verify_main.py`
* `src/core/drug_matching/config/config_helpers.py` (×2)
* `src/core/drug_matching/pipeline.py`
* `src/core/drug_matching/pipeline_components/pipeline_io.py`
* `src/core/drug_matching/pipeline_components/pipeline_matching.py`
* `src/core/drug_matching/tracing/trace_log.py`
* `src/core/drug_matching/tracing/trace_log_output.py`
* `src/core/drug_matching/verification/verifier_request_parse.py`
* `src/core/drug_matching/verification/verifier_request_validate.py`
* `src/core/drug_matching/verification/verifier_response.py`
* `src/core/matching/matching_trace.py`
* `src/cli/commands/cli_match_products.py`

### `_console_safe()` usage (4)

* `src/tawreed/order/tawreed_order_summary.py` (×3)
* `src/tawreed/tawreed_bot_core.py` (×1)

`_console_safe` was a workaround for Windows console encoding issues.
The unified logging_setup writes UTF-8 to all handlers, so this wrapper
is no longer necessary and can be deleted in stage 2.

### Manual handler manipulation (1)

* `src/core/matching/matching_trace.py:34` — `logger.handlers = []`
  (part of the now-deprecated `configure_async_logging`).

This was already weakened in commit `280e733` so the matching logger
inherits from root. The line is harmless (clears an empty list) but
should be removed in stage 3 for clarity.

### Files using the `__name__` convention (10)

These are the files we touched in stages 1 + 2. Stage 3 will add the
remaining ~20 files (mostly `src/core/drug_matching/` modules currently
using the literal `"pharmasupplybot.matching"`).

## Acceptance criteria for the unification plan

| Stage | Acceptance metric | Baseline | Target |
|-------|-------------------|---------:|-------:|
| 2     | `print()` in `src/`        |    27 |     0 |
| 3     | `"pharmasupplybot.matching"` literals |    20 |     0 |
| 3     | `_console_safe()` calls    |     4 |     0 |
| 3     | Manual handler manipulation |   1 |     0 |
| 4     | Files using `__name__` convention | 10 |   30 |

When stage 6 is complete, re-running `py scripts/audit_logging.py`
must produce zeroes (or near-zero) for the left-hand column.

## Tool re-run

```bash
py scripts/audit_logging.py
```

The script:
1. Walks `src/` once using `ast.walk` (no regex)
2. Writes `docs/audit_logging.md` with the same data
3. Exits 0 always — it is a report, not a gate

The CI guard tests in `tests/core/test_logging_audit.py` (stage 4) will
turn these findings into hard failures.