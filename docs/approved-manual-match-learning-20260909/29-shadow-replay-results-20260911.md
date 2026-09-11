# Shadow Replay Results - 2026-09-11

## Scope

The replay used the same 799 eligible order rows, the same two Excel target
workbooks, match-only mode, and four item workers. The feature flag was
enabled only for the shadow run and was removed from state/config.yaml
afterward.

The corrected implementation wires review aliases produced by the local
Tawreed/dictionary index into the review discovery index. A regression test
failed before this wiring change and passed after it.

## A/B runs

The corrected code was run twice:

- Run 20260911_1430: cross-language review aliases enabled.
- Run 20260911_1436: cross-language review aliases disabled.

Both runs completed in match-only mode without submitting orders.

| Target | A/B result | Manual-review items | Saved candidates | p50 / p95 / p99 / max |
|---|---:|---:|---:|---:|
| Baraka companies | identical | 105 | 217 | 0 / 2 / 4 / 11 |
| Qaysar companies | identical | 149 | 278 | 0 / 2 / 4 / 16 |

The candidate JSONL files were byte-identical between the two runs. The
semantic summary rows were also identical; only runtime metadata such as
elapsed time differed.

No saved candidate used the method cross_language_alias. The existing aliases
were already represented by review_identity or review_identity_prefix and were
deduplicated by the same target row key. Therefore the new flag produced no
observable candidate increase on this 799-item replay.

## Automatic-match safety

The target counters were unchanged between the enabled and disabled A/B runs:

- Baraka: 154 matched, 645 flagged.
- Qaysar: 109 matched, 690 flagged.

The feature did not turn review-only evidence into an automatic match. The
flag remains disabled in the working configuration.

## Golden rows

The previously recovered rows remain present in the review candidate artifacts:

- VOLTAREN 3AMP: Baraka row 3100; Qaysar row 2798.
- XITHRONE 500MG 3TAB: Baraka row 2345; Qaysar row 2148.

These are recall checks only. They are not automatic-match approvals, because
the product form and pack compatibility still require human confirmation.

## Decision

Do not enable the feature in production based on this replay. The result is
safe but neutral: it confirms no regression and no added recall on this input.

The next useful step is to create a separate, human-reviewed alias proposal
set from genuinely no-candidate English/Arabic cases. An approved proposal
must be target-scoped, have positive and negative gold examples, and remain
review-only. Manual decisions must not be promoted automatically into global
aliases.

Two rollout gates remain open:

1. A labeled positive/negative alias set large enough to measure precision.
2. Explicit C_display measurement in the manual-review UI.
