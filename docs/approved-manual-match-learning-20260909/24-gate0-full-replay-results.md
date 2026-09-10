# Gate 0 and Full Replay Results

Date: 2026-09-10

## What was executed

The operational command from the runbook was executed in `--match-only` mode,
without a limit, using the current input workbook and the existing safe policy.
The input workbook available in the workspace contains 961 physical rows; 799
items were eligible after prevented-item filtering. No order submission was
performed.

Run artifact: `artifacts/order/wardany/20260910_1243`

## Full replay result

| Target | Eligible rows | Automatic matches | Manual-review rows | Generated/union candidates | Saved candidates |
|---|---:|---:|---:|---:|---:|
| البركة شركات | 799 | 153 | 108 | 221 | 221 |
| القيصر شركات | 799 | 109 | 149 | 278 | 278 |

The automatic match counts are target-scoped and remain separate from the
review-only candidate counts. The current artifacts contain no explicit UI
display count, so `C_display` is reported as `null`, not inferred from the
saved count.

## Candidate-count tails

| Target | C_generated p50 | p95 | p99 | max | C_saved p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| البركة شركات | 0 | 2 | 4 | 11 | 0 | 2 | 4 | 11 |
| القيصر شركات | 0 | 2 | 4 | 16 | 0 | 2 | 4 | 16 |

These are volume and coverage measurements, not precision measurements.
Precision remains unmeasured until a human-labelled gold/negative set is
adjudicated. The proposed sampling procedure is documented in
`19-precision-sampling-report.md`.

## Gate 0 changes completed

- Added a save-cap regression proving `candidate_count_total=4`,
  `candidate_count_saved=2`, and two persisted options.
- Added the read-only report tool
  `tools/report_excel_target_candidate_coverage.py`.
- The report validates duplicate item records, summary/envelope count
  consistency, and `saved <= generated`.
- Preserved `excel_target_row_key` during loader and Streamlit deduplication.
- Added `ranking_tier` to the generic candidate model and its JSONL round-trip.
- Added tests for two physical Excel rows that share product identity fields but
  have different row keys.

## Remaining rollout gates

Gate 0 is improved but not fully closed. Before adding a cross-language review
channel, the remaining checks are:

1. Emit or otherwise measure the actual UI `C_display` after source merge,
   source-diversity filtering, and display limit.
2. Add an end-to-end test for JSONL -> loader -> Streamlit merge with duplicate
   product identity and distinct physical row keys.
3. Expand automatic isolation tests to fail closed for unknown/future evidence
   kinds and verify no auto-save/rebind is triggered by review-only candidates.
4. Re-run the full Excel-target suite and compare the automatic matched set
   against the pre-change replay.

Until those checks pass, do not lower fuzzy thresholds, add transliteration to
automatic identity, or enable a new cross-language channel.
