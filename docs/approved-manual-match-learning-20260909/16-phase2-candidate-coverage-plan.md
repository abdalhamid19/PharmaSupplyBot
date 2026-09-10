# Phase 2 Candidate Coverage Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Increase useful Excel-target manual-review coverage and candidate recall
without allowing review-only evidence to produce an automatic match.

**Architecture:** Keep automatic identity and compatibility as a separate
decision plane. Build a bounded review plane with explicit evidence tiers,
target-scoped row provenance, deterministic ranking, and separate coverage
metrics. Expand cross-language discovery only after the safety and ranking
contracts are tested.

**Tech Stack:** Python 3.11, dataclasses, RapidFuzz, pytest, JSONL/CSV
artifacts, existing Excel-target matcher and manual-review store.

**Spec:** 09-candidate-recall-implementation-plan.md,
12-identity-absent-expansion-analysis.md, 13-cross-language-candidate-recall-analysis.md,
14-ranking-and-metrics-analysis.md, and 15-phase2-plan-review.md.

## Global Constraints

- review_identity, review_fuzzy, and future discovery_only evidence are
  review-only and must never produce best_match.
- Do not lower discovery thresholds or add transliteration to automatic identity.
- Every candidate must resolve to a row in the currently loaded target catalog.
- Preserve target_key, source_file, source_row_number, and excel_target_row_key.
- Keep candidate_count_total separate from saved and displayed counts.
- Keep deterministic ordering for the same catalog, configuration, and item.
- Preserve the negative behavior: identity absent with no candidate does not
  enter the candidate queue.
- Do not mutate production SQLite or input workbooks during unit tests.
- Run replay measurements before changing discovery thresholds.

## File Map

- src/core/excel_target/excel_target_matching.py: automatic safety gate and
  review/automatic plane boundary.
- src/core/excel_target/excel_target_review_candidates.py: evidence tiers,
  candidate ranking, row-key deduplication, and ranking metadata.
- src/core/excel_target/excel_target_review_discovery.py: bounded discovery;
  later tasks may add target-scoped cross-language channels.
- src/cli/commands/cli_order_excel_target.py: review artifact counts and
  source provenance.
- tests/core/excel_target/test_excel_target_candidate_recall.py: review-only
  safety and anchored recall tests.
- tests/core/excel_target/test_excel_target_review_candidates.py: ranking and
  dedup tests.
- tests/cli/commands/test_excel_target_manual_review_artifacts.py:
  identity-absent discovery artifact contract.

## Task 1: Lock the review-only safety boundary

**Files:**

- Modify: src/core/excel_target/excel_target_matching.py
- Test: tests/core/excel_target/test_excel_target_candidate_recall.py

**Interfaces:**

- Consumes: IdentifiedTarget, IdentityEvidence, and Item.
- Produces: rejection of review-only evidence in the automatic decision gate.

- [x] Add a test that passes a compatible-looking review_identity candidate to
  _compatible_identified and asserts it is rejected; assert _identity_decision
  also rejects it when called directly.
- [x] Reject review_identity and review_fuzzy explicitly alongside the existing
  cohere_translation manual-review rejection.
- [x] Run:

~~~powershell
& '.venv\Scripts\python.exe' -m pytest tests\core\excel_target\test_excel_target_candidate_recall.py -q
~~~

## Task 2: Lock identity-absent discovery artifact behavior

**Files:**

- Modify: tests/cli/commands/test_excel_target_manual_review_artifacts.py
- Inspect: src/cli/commands/cli_order_excel_target.py

- [x] Add a positive test where identified is empty but a bounded
  ReviewDiscoveryHit exists. Assert manual_review_required=True,
  manual_review_category=excel_target_candidate_available, candidate_method is
  english_fuzzy, and best_match remains None.
- [x] Keep the negative no-hit identity-absent test asserting no manual-review
  artifact.
- [x] Run the artifact tests.

## Task 3: Rank candidates by evidence tier, not incomparable scores

**Files:**

- Modify: src/core/excel_target/excel_target_review_candidates.py
- Test: tests/core/excel_target/test_excel_target_review_candidates.py

**Interfaces:**

- Produces: ExcelTargetReviewCandidate.ranking_tier -> int.
- Produces: persisted option field ranking_tier.
- Consumes: existing evidence kinds and compatibility result.

- [x] Add a collision test: one review_identity and one higher-scoring
  english_fuzzy hit for the same row; retain review_identity.
- [x] Define tiers: 0 trusted compatible identity, 1 trusted rejected or
  unproven identity, 2 anchored review_identity, 3 review_fuzzy/english_fuzzy/
  arabic_fuzzy, and 4 unknown future review evidence.
- [x] Use the tier for deduplication and final ordering. Within a tier use
  compatibility bucket, score, score margin, and ascending row key.
- [x] Persist ranking_tier without replacing candidate_method or provenance.
- [x] Run the ranking tests.

## Task 4: Add measurable review-universe counters

**Files:**

- Inspect/modify: src/cli/commands/cli_order_excel_target.py
- Test: tests/cli/commands/test_excel_target_manual_review_artifacts.py
- Create: tools/report_excel_target_candidate_coverage.py

- [x] Add an artifact regression with more candidates than the save limit.
  Assert the total is the generated union and saved count is capped.
- [x] Add a read-only report tool that calculates coverage, recall, and
  precision samples without writing SQLite or input workbooks. The report
  leaves C_display null unless the UI emits an explicit display count.
- [x] Run the report against historical Baraka/Qaysar artifacts and record
  p50, p95, p99, and maximum candidate counts.

Gate note: Task 4 measurement is usable for generated/union/saved counts, but
the rollout gate remains open until the UI display count and full round-trip
invariants are covered by an end-to-end test.

## Task 5: Add target-scoped cross-language review discovery

**Files:**

- Modify: src/core/excel_target/excel_target_review_discovery.py
- Modify: src/core/excel_target/excel_target_matching.py
- Test: tests/core/excel_target/test_excel_target_review_discovery.py
- Test: tests/core/excel_target/test_excel_target_candidate_recall.py

- [ ] Add an English-query/Arabic-only-catalog failing test with a generic alias
  fixture.
- [ ] Implement a review-only alias channel resolved to rows in the current
  catalog only; do not call live translation or network services.
- [ ] Add negative tests for short roots, shared prefixes, manufacturer-only
  suffixes, and unrelated brands.
- [ ] Run the full Excel-target suite and compare automatic results before and
  after.

## Task 6: Controlled discovery expansion

**Files:**

- Modify: src/core/excel_target/excel_target_review_discovery.py
- Modify: state/config.yaml only after replay approval
- Test: tests/core/excel_target/test_excel_target_review_discovery.py

- [ ] Keep thresholds unchanged by default and add a separate feature gate for
  any new discovery channel.
- [ ] Run shadow replay with positive and negative gold cases.
- [ ] Stop rollout if candidate-count p99 or reviewed precision exceeds the
  declared budget.
- [ ] Enable only after artifact and safety acceptance gates pass.

## Acceptance Gates

- No automatic match contains review_identity, review_fuzzy, or future
  discovery_only evidence.
- Discovery-only identity-absent items enter manual review only when they have
  a bounded candidate.
- No-hit identity-absent items remain outside the candidate queue.
- Anchored candidates are not displaced by higher numeric fuzzy scores for the
  same row.
- Every candidate remains target/source/row-key scoped.
- candidate_count_total >= candidate_count_saved >= 0.
- Ordering is deterministic across repeated runs and worker counts.
- Golden rows 3100 and 2345 remain present.
- Automatic match counts do not increase because of review-only evidence.

## Verification Commands

~~~powershell
& '.venv\Scripts\python.exe' -m pytest tests\core\excel_target tests\cli\commands\test_excel_target_e2e.py tests\cli\commands\test_excel_target_manual_review_artifacts.py -q
& '.venv\Scripts\python.exe' -m compileall -q src\core\excel_target tests\core\excel_target
git diff --check
~~~

The full operational replay remains the command documented in
10-before-after-runbook.md. Rerun it only after the phase has a measured
change to retrieve or rank candidates.
