# Before/after runbook: Excel-target manual-review recall

## Baseline

The first same-input replay before the fix was completed on 2026-09-10 as
`artifacts/order/wardany/20260910_1051`:

| Scope | Processed | Matched | Flagged | Manual review |
|---|---:|---:|---:|---:|
| Tawreed/order | 100 | 61 | 11 | n/a |
| البركة شركات | 100 | 22 | 78 | 0 |
| القيصر شركات | 100 | 16 | 84 | 6 |

The exact replay uses `--limit 100`; the two reported examples occur after
that first page, so they are not present in the 100-row Baraka artifact.
The historical full relevant replay
`artifacts/excel-target/البركة شركات/20260909_1457` and the focused
pre-change matcher replay established the actual recall failure:

- `VOLTAREN 3AMP`: row 3101 was saved; row 3100 was absent.
- `XITHRONE 500MG 3TAB`: row 2344 was saved; row 2345 was absent.

The focused pre-change replay returned one candidate for each item, with
`decision.best_match is None`.

## Focused before/after check

Use `ExcelTargetMatcher(..., use_saved_approvals=False)` with
`data/input/excel target/محروس1.xlsx` and source file label `محروس1.xlsx`.
The after-state must contain rows 3100 and 2345 in `review_candidates`, retain
their row keys and source metadata, and keep `decision.best_match is None`.
The observed after-state is:

- `VOLTAREN 3AMP`: 8 candidates; row 3100 is present and row 3102 is also
  included as a same-brand row with an extra descriptor.
- `XITHRONE 500MG 3TAB`: 3 candidates; row 2345 is present.
- Both automatic decisions remain `None`.

## Full replay command

```powershell
$stop='artifacts\run-control\order\order\_stop.flag'
& '.venv\Scripts\python.exe' 'run.py' order --config 'state\config.yaml' --excel 'data\input\order_items\09092026.xlsx' --limit 100 --all-profiles --excel-target 'البركة شركات' --excel-target-path 'البركة شركات=C:\pc\py\pyreview\PharmaSupplyBot\data\input\excel target\محروس1.xlsx' --excel-target 'القيصر شركات' --excel-target-path 'القيصر شركات=C:\pc\py\pyreview\PharmaSupplyBot\data\input\excel target\جملة محروس.xlsx' --execution-mode api --item-workers 4 --prevented-items-excel 'data\input\prevented_items\drugprevented.xlsx' --matching-risk-policy safe --flagged-match-action manual-review-only --stop-flag $stop --match-only
```

Record the new artifact directories and compare processed/matched/flagged/manual
review totals, candidate row keys, candidate methods, compatibility statuses,
and target/source provenance. Ignore run timestamps and elapsed milliseconds.

The valid after replay completed as
`artifacts/order/wardany/20260910_1145` with the same aggregate totals as the
baseline:

| Scope | Processed | Matched | Flagged | Manual review |
|---|---:|---:|---:|---:|
| Tawreed/order | 100 | 61 | 11 | n/a |
| البركة شركات | 100 | 22 | 78 | 0 |
| القيصر شركات | 100 | 16 | 84 | 6 |

Because the examples are outside `--limit 100`, the aggregate run is a
pipeline regression check; the focused real-catalog replay is the gold-case
candidate-recall check.

## Acceptance gates

- Both correct rows appear in `review_candidates` for the focused Baraka
  replay; the exact `--limit 100` artifact does not include those later input
  rows.
- `candidate_count_total >= candidate_count_saved >= 0` for every record.
- No candidate source is Tawreed or another Excel target.
- No `review_identity` candidate becomes an automatic match.
- Candidate ordering is deterministic for a fixed catalog and config.
- Existing Excel-target and manual-review test suites remain green.
