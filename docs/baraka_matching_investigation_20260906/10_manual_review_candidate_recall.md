# Baraka manual-review candidate recall runbook

## Purpose

This runbook measures whether the Excel-target review-only layer finds more
human-review candidates without changing the verified automatic-match set.
Variant conflicts are useful review evidence: a likely same-brand row remains a
candidate when its form, concentration, strength, or pack differs. Such a row
must not become an automatic match.

## Configuration

The conservative review-discovery settings are stored under `matching` in
`state/config.yaml`:

```yaml
excel_target_review_candidates_enabled: true
excel_target_review_candidate_limit: 5
excel_target_review_fuzzy_strong_score: 90.0
excel_target_review_fuzzy_strong_margin: 8.0
excel_target_review_fuzzy_medium_score: 86.0
excel_target_review_fuzzy_medium_margin: 12.0
excel_target_review_ambiguous_score: 88.0
excel_target_review_ambiguous_margin: 8.0
```

The saved-candidate limit remains controlled separately by
`manual_review_save_candidate_limit` (currently 30). The report distinguishes
the total discovered candidates from the number saved after that limit.

Normal `--match-only` index construction may use Cohere. It must retain the
existing batch size, cache lookup, rate limiter, monthly quota, key failover,
and provenance behavior. Review-candidate discovery itself is local and must
not call Cohere or write the translation cache.

## Staged evaluation

Generate the before/after reports in separate artifact directories, then run:

```powershell
& ".venv\Scripts\python.exe" scripts\evaluate_excel_target.py `
  --before "artifacts\excel-target\البركة شركات\baseline\baraka_coverage.csv" `
  --after "artifacts\excel-target\البركة شركات\candidate-recall-50\baraka_coverage.csv" `
  --output "artifacts\excel-target\البركة شركات\candidate-recall-50\review_candidate_diff.json"
```

The evaluator is CSV-only. It does not open SQLite, read `.env`, call a
provider, or write production state. Parallel evaluations must use distinct
temporary input/output directories.

The output compares:

- `matched_set_before` and `matched_set_after`, keyed by item code, item name,
  and selected target product ID;
- `new_review_items` and `removed_review_items`;
- per-run counts for matched, manual review, identity absence, variant
  rejection, and Excel-target candidate availability;
- candidate codes, candidate categories, and optional human labels;
- safety errors for fuzzy/Cohere/rejected-compatibility rows promoted to
  `matched`;
- independent `gold_labels.csv` category and selected-product checks.

## 200-item replay

Use the approved command with an isolated run-control/artifact root when
testing. The expected target summary is written below the generated
`artifacts/excel-target/البركة شركات/<run-id>/` directory.

```powershell
& 'C:\pc\py\pyreview\PharmaSupplyBot\.venv\Scripts\python.exe' '.\run.py' order --config 'state\config.yaml' --excel 'data\input\order_items\0000000000006777.xlsx' --limit 200 --all-profiles --excel-target 'البركة شركات' --excel-target-path 'البركة شركات=data\input\excel target\البركة شركات.xlsx' --match-only --execution-mode api --item-workers 1 --prevented-items-excel 'data\input\prevented_items\drugprevented.xlsx' --matching-risk-policy safe --flagged-match-action manual-review-only --stop-flag 'artifacts\run-control\order\order_stop.flag'
```

For every summary row verify:

```text
manual_review_required == (review_candidate_count_total > 0)
```

The saved count may be lower than the total count. A new review row is valid
only when it has target provenance, a stable row key, a candidate method or
identity evidence, a score, and a compatibility status (`compatible`,
`rejected`, or `unknown`). A `rejected` or `unknown` variant is still reviewable
when the brand anchor is strong; it is never automatically accepted.

## Saved correction approval

When a reviewer selects a candidate, the Saved Corrections (Manual Review
Store) record must contain `manual_decision=approved_match`, `approved=1`, the
target key, and the exact Excel row identity. The later replay may promote that
same scoped row despite a form, concentration, strength, or pack conflict.

The promoted result is reported as `manual_review_rebound` with
`approved_manual_override` provenance. It is not counted as a new automatic
fuzzy match. Missing, stale, duplicated, or differently scoped row identity
keeps the item in manual review.

## Rollback

If the new candidates are noisy, set
`excel_target_review_candidates_enabled: false` and rerun the evaluator. This
disables review-only discovery while preserving the existing verified matching
path. Do not relax automatic identity or compatibility thresholds to increase
the review count.
