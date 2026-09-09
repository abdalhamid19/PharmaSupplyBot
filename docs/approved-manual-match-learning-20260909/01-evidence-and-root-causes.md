# Evidence and Root-Cause Taxonomy

## Reproduction baseline

The requested command was run on 2026-09-09 using `run.py` (the pasted Markdown
link around the filename was normalized to the actual local script). The stop
flag was absent. The run completed successfully in 43 seconds:

| Scope | Processed | Matched | Flagged | Manual review |
|---|---:|---:|---:|---:|
| Tawreed/order | 100 | 62 | 11 | n/a |
| البركة شركات | 100 | 22 | 78 | 0 |
| القيصر شركات | 100 | 16 | 84 | 6 |

Artifacts are under `artifacts/order/wardany/20260909_1826` and
`artifacts/excel-target/<target>/20260909_1826`. These are production-style
artifacts, so future automated tests must instead use temporary DBs and copied
workbooks.

## What “failed initially” means

For each later-approved row, reconstruct the decision as though the approval
were absent. Do not infer the reason from the final `matched` status: a saved
decision short-circuits normal candidate selection. Persist the first failing
gate and all relevant evidence:

| Root-cause code | Evidence from current matcher | Safe remediation class |
|---|---|---|
| `identity_absent` | no verified bilingual/alias identity | add audited alias or improve catalog/dictionary coverage |
| `cohere_review_only` | identity is Cohere-derived | preserve review-only policy; seek deterministic alias evidence |
| `variant_conflict` | form, strength, concentration, or pack differs | retain manual override only; never generalize automatically |
| `ambiguous_identity` | more than one compatible verified target row | improve row identity or require reviewer choice |
| `native_score_below_threshold` | English target candidate loses existing safe score gates | add exact normalized alias only after labeled evaluation |
| `stale_or_missing_row` | saved row key cannot bind uniquely | re-review; never fall back to name-only promotion |
| `source_scope_mismatch` | decision belongs to another target | data-quality repair only |

The current CSV examples show `identity_absent` for Arabic-only candidates
without verified brand identity, while the manual-review CSV contains genuine
same-brand candidates rejected for form or strength differences. Those latter
cases are exactly why a human approval must remain row-scoped.

## Metrics and acceptance criteria

Report separate counts for automatic verified matches and approved overrides.
No aggregate “matched improved” metric may hide an increase in false automatic
matches.

- zero auto-matches with `review_fuzzy` or `cohere_translation` evidence;
- zero auto-matches with rejected compatibility except a valid
  `approved_manual_override`;
- every applied approval has target key, workbook, row number, and row key;
- every approved item has exactly one root-cause classification;
- recommendation output is deterministic and contains evidence counts;
- newly automated rules require a labeled evaluation pass with no false
  positives in the gold set and explicit human sign-off.
