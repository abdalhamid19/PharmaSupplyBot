# Approved Manual Match Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `executing-plans` and TDD
> task-by-task. Steps use checkbox syntax.

**Goal:** increase safe `automatic_verified` Excel-target matches by finding
why previously `approved_match` items were not matched initially, then applying
only evidence-backed deterministic improvements without weakening safety.

**Architecture:** add a pure counterfactual analyzer beside the Excel-target
matcher; expose it through a CLI report and a read-only Streamlit view. The
existing exact-row approval path remains the only variant-conflict override.

**Tech Stack:** Python 3.10+, dataclasses, SQLite, CSV/JSON, pytest,
Streamlit, existing `scripts/evaluate_excel_target.py`.

**Spec:** `docs/approved-manual-match-learning-20260909/README.md` and
`docs/approved-manual-match-learning-20260909/02-architecture.md`.

## Global constraints

- Do not read, print, commit, or test with secrets from `.env`.
- Do not mutate production `state/*.db` in tests or report generation.
- The counterfactual matcher must disable saved approvals through an explicit
  injected lookup or `use_saved_approvals=False`; it must never call a rebind
  recorder or `ManualReviewStore.upsert`.
- Do not auto-promote fuzzy/Cohere-only evidence or a compatibility rejection.
- Only a uniquely binding `approved_match` with exact target-row provenance may
  yield `approved_manual_override`.
- Keep manual review and automatic matching metrics separate.
- Treat `approved_match` as labeled diagnostic evidence only; it never counts
  as an automatic-matching improvement in before/after reporting.

## File structure

- Create `src/core/excel_target/approved_correction_analysis.py`: pure
  snapshot/counterfactual analysis and classification.
- Create `src/cli/commands/cli_approved_correction_report.py`: explicit CLI
  adapter that writes JSON and CSV.
- Modify `run.py`/existing CLI registration module: register a report command
  without changing `order` semantics.
- Modify `src/ui/manual_review/streamlit_manual_review_page_saved.py`: link to
  latest report and render a read-only root-cause aggregate.
- Create focused tests under `tests/core/excel_target`, `tests/cli/commands`,
  and `tests/ui/manual_review`.

### Task 1: Freeze counterfactual inputs and baseline

**Files:** create `tests/core/excel_target/test_approved_correction_analysis.py`;
create `tests/core/excel_target/fixtures/approved_corrections.csv`.

- [ ] Write a failing test with a valid row-scoped approved decision whose
  ordinary match is absent; assert one finding with `identity_absent`.
- [ ] Write failing tests for `variant_conflict`, `cohere_review_only`,
  `ambiguous_identity`, stale row key, wrong target key, duplicate current
  rows, and an approval whose ordinary match now succeeds.
- [ ] Run `& '.venv\Scripts\python.exe' -m pytest tests\core\excel_target\test_approved_correction_analysis.py -q` and verify failure because the module is absent.
- [ ] Copy only sanitized fixtures into a temporary SQLite DB; assert hashes of
  `state/manual_review_decisions.db` and `state/order_runs.db` are unchanged.
- [ ] Commit: `test: define approved correction counterfactual cases`.

### Task 2: Implement pure analysis and taxonomy

**Files:** create `src/core/excel_target/approved_correction_analysis.py`; modify
the Task 1 test.

- [ ] Add `use_saved_approvals: bool = True` to `ExcelTargetMatcher` and test
  that `False` bypasses `_scoped_manual_review` and never records a rebind.
- [ ] Define `ApprovedCorrectionFinding`, `RuleRecommendation`, and
  `ApprovedCorrectionReport` exactly as documented in the architecture file.
- [ ] Implement `analyze_approved_corrections(decisions, catalogs,
  matching_config, matcher_factory) -> ApprovedCorrectionReport`; filter to
  `matching_source == 'excel-target'`, `manual_decision == 'approved_match'`,
  and `approved is True`.
- [ ] For each decision, validate `excel_target_key` and exact row key before
  replaying with a matcher that cannot see saved approvals.
- [ ] Classify in fixed priority order: stale/scope failure, ambiguous,
  rejected variant, Cohere-only, no verified identity, score threshold, then
  `unexpected_counterfactual_match`.
- [ ] Classify decisions lacking complete target/row provenance as
  `legacy_invalid`; list approvals outside the supplied order-item dataset as
  `approval_outside_current_input`, not as matching failures.
- [ ] Generate recommendations only for repeated `identity_absent` or
  `native_score_below_threshold` groups; mark every recommendation
  `requires_human_approval=True` and include sample item/row keys.
- [ ] Run focused tests; commit: `feat: analyze approved Excel corrections`.

### Task 3: Add report command and artifacts

**Files:** create `src/cli/commands/cli_approved_correction_report.py`; modify
the CLI registration; create `tests/cli/commands/test_cli_approved_correction_report.py`.

- [ ] Write a failing CLI test using temporary workbook/DB paths. Assert JSON
  and UTF-8-SIG CSV are emitted under a caller-selected artifact directory and
  that no store `upsert` is called.
- [ ] Implement `approved-correction-report --excel-target KEY
  --excel-target-path KEY=PATH --output DIR`; reject duplicate target keys and
  missing paths with a non-zero exit.
- [ ] Include report schema version, generated time, target catalog fingerprint,
  counts, findings, and recommendations in JSON. CSV has one row per finding.
- [ ] Add explicit `match_origin` to new match-only artifacts
  (`automatic_verified`, `approved_manual_override`, or `saved_auto_matched`)
  and regression-test that readers need not parse `final_reason`.
- [ ] Run focused CLI tests; commit: `feat: export approved correction report`.

### Task 4: Present and govern recommendations

**Files:** modify `streamlit_manual_review_page_saved.py`; create
`tests/ui/manual_review/test_saved_correction_report.py`; create
`docs/approved-manual-match-learning-20260909/04-operations.md`.

- [ ] Write a failing UI helper test asserting root-cause counts and stale
  approvals render without exposing the raw database path or mutating a row.
- [ ] Add a read-only expander for the latest selected report: counts, samples,
  stale approvals, and recommendation evidence. No “apply rule” button.
- [ ] Document the human approval checklist: inspect all candidate aliases,
  add gold cases, test a single deterministic rule, rerun shadow evaluation,
  and audit every new auto-match.
- [ ] Run focused UI tests; commit: `feat: show approved correction audit`.

### Task 5: Verification and controlled rollout

- [ ] Run focused analysis/CLI/UI tests plus
  `tests/core/excel_target/test_baraka_safe_matching.py`.
- [ ] Run `& '.venv\Scripts\python.exe' scripts\evaluate_excel_target.py --before <baseline.csv> --after <candidate.csv> --output <comparison.json>`; require empty `safety_errors` and passing gold validation.
- [ ] Run `& '.venv\Scripts\python.exe' tools\rule_audit.py` and the relevant
  unit-test discovery command used by CI.
- [ ] Run the user’s exact 100-item order command before and after code changes,
  preserving its stop flag behavior. Compare each target’s processed/matched/
  flagged/manual-review totals and list new automatic rows by evidence kind.
- [ ] Manually inspect every new automatic match for brand, modifier, form,
  strength/concentration, and pack. Reject the rollout if any fails.
- [ ] Create an approval-disabled baseline for the same inputs. Compare
  improvements to that counterfactual as well as production; otherwise saved
  approvals would be misreported as feature gains.
- [ ] Calculate and publish only this primary improvement metric:
  `automatic_verified_after - automatic_verified_before`. Publish
  `approved_manual_override` as a separate informational count and fail the
  rollout if an apparent gain consists solely of existing manual overrides.
- [ ] Commit final docs and report fixtures; push only the commits created for
  this feature, after confirming the branch and remote.
