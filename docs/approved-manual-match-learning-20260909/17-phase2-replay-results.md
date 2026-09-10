# Phase 2 bounded candidate-coverage replay

## Scope

This replay validates the first phase of the second rollout:

- explicit review-only safety barriers;
- deterministic evidence-tier ranking;
- anchored review aliases that work even when the target has no bare Arabic
  brand row;
- prefix anchors labeled separately as lower-confidence review evidence.

No discovery threshold was lowered and no review-only evidence was added to the
automatic identity path.

## Verification

The full relevant suite passed:

~~~text
188 passed, 2 subtests passed
~~~

The final operational replay completed at:

~~~text
artifacts/order/wardany/20260910_1233
~~~

The same command used for the previous after-run was used with the same input,
configuration, target workbooks, limit, workers, safe-risk policy, and
match-only mode.

| Scope | Processed | Matched | Flagged | Manual review |
|---|---:|---:|---:|---:|
| Tawreed/order | 100 | 61 | 11 | n/a |
| البركة شركات | 100 | 22 | 78 | 7 |
| القيصر شركات | 100 | 16 | 84 | 16 |

For comparison, the previous bounded replay at
artifacts/order/wardany/20260910_1145 had manual-review totals of 0 for
Baraka and 6 for Qaysar. Automatic match counts are unchanged.

The final target artifacts reported:

| Target | Rows | identity_absent | candidate-review rows | Candidate union |
|---|---:|---:|---:|---:|
| البركة شركات | 100 | 71 | 7 | 8 |
| القيصر شركات | 100 | 68 | 16 | 26 |

The increased queue is a coverage signal, not a precision claim. The next
phase must sample the new candidates against positive and negative gold cases
before any threshold is relaxed further.

## Safety result

- review_identity and review_identity_prefix remain manual-review evidence.
- review_fuzzy remains manual-review evidence.
- No new automatic match was produced by these evidence types.
- Candidate provenance remains target-scoped with workbook and row metadata.
- The no-hit identity_absent negative control still produces no candidate
  artifact.

## Next checkpoint

Before implementing broad transliteration or lower fuzzy thresholds:

1. measure candidate-count p50/p95/p99/max on a full replay;
2. inspect a bounded precision sample of the seven Baraka and sixteen Qaysar
   new review groups;
3. add gold positives and near-negative cases for any new alias family;
4. decide whether to proceed with target-scoped cross-language discovery.
