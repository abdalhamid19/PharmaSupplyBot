# Excel-target Manual-review Candidate Recall Implementation Plan

> **For agentic workers:** Use the repository's TDD and systematic-debugging practices. Execute the checked tasks in order and keep each task independently testable.

**Goal:** Make manual-review artifacts contain every bounded, same-identity Excel-target row that a reviewer may need to inspect, including `فولتارين 3مبول س جديد` for `VOLTAREN 3AMP` and `زيثرون 3قرص س جديد` for `XITHRONE 500MG 3TAB`, without weakening automatic-match safety.

**Architecture:** Add a review-only identity expansion beside the existing exact identity index. It will use audited Tawreed/dictionary bilingual aliases as an anchor, then include target rows whose normalized Arabic name starts with that anchored Arabic brand. The expansion will feed `review_candidates` only; `_compatible_identified` and the automatic decision path will continue to use the existing exact identity index.

**Tech Stack:** Python 3.11, dataclasses, RapidFuzz-independent normalization, existing Excel loader/matcher, JSONL/CSV artifacts, pytest/unittest.

**Spec:** `docs/approved-manual-match-learning-20260909/01-evidence-and-root-causes.md`, `06-candidate-recall-code-map.md`, `07-baseline-data-analysis.md`, and `08-test-and-metrics-strategy.md`.

## Global constraints

- Preserve all unrelated working-tree changes already present in `src/core/excel_target`, `tests/core/excel_target`, `state`, and input workbooks.
- Never use a review-only candidate as automatic evidence; only the existing exact identity plus compatibility gate may produce an automatic Excel-target match.
- Keep the existing `manual_review_save_candidate_limit` and `manual_review_display_candidate_limit` contracts. Report total generated candidates separately from saved/displayed candidates.
- Every saved option must retain `target_key`, `source_file`, `source_row_number`, and the stable Excel row key.
- Do not call network translation, Cohere, or Tawreed APIs from the review-only expansion.
- Candidate ordering must be deterministic for the same catalog, configuration, and input.
- Test with temporary or in-memory fixtures where possible; do not mutate production SQLite databases during unit tests.
- The user command is an operational replay and may write artifacts/state. Record its run directory and compare semantic output, not volatile timestamps.

## Evidence and current failure

The baseline run `wardany/20260909_1457` loaded `محروس1.xlsx` successfully. The workbook contains the expected rows at source rows 3100 and 2345, but the manual-review JSONL contained only one wrong candidate for each item. The current normalization produces keys equivalent to:

```text
فولتارين 3مبول س جديد -> فولتارين 3مبول س
فولتارين 50مجم - 20قرص -> فولتارين
زيثرون 3قرص س جديد -> زيثرون س
زيثرون 500-- 5قرص -> زيثرون
```

The exact identity index therefore anchors `VOLTAREN` and `XITHRONE` to the wrong rows. The fuzzy review discovery then selects one language projection; an English request cannot discover Arabic-only rows. The artifact writer correctly serializes the candidates it receives, so changing the writer limit alone cannot fix recall.

## File map

- Modify `src/core/excel_target/excel_target_identity.py`:
  - Add a review-only Arabic brand normalizer that removes audited packaging/status decorations such as fused `3مبول`, `3امبولة`, `3قرص`, and `س جديد`.
  - Build a first-token index over target rows and review alias maps anchored by an existing exact Arabic alias hit.
  - Add `identify_review_candidates(item_name)` returning `IdentifiedTarget` values with an explicit `review_identity` evidence kind.
  - Leave `identify(item_name)` and its automatic identity maps unchanged.
- Modify `src/core/excel_target/excel_target_matching.py`:
  - Call the new review-only identity method after the normal identity lookup.
  - Merge normal identity candidates, review-only identity candidates, and fuzzy discovery candidates only for `build_review_candidates`.
  - Keep `_compatible_identified` fed only by normal identity candidates.
- Modify `src/core/excel_target/excel_target_review_candidates.py`:
  - Map `review_identity` to a clear persisted `candidate_method`.
  - Preserve current row-key, source, compatibility, and ordering behavior.
- Modify `tests/core/excel_target/test_excel_target_identity_normalization.py`:
  - Add the two Arabic normalization regression cases and a near-negative that must retain a meaningful brand suffix.
- Modify `tests/core/excel_target/test_excel_target_review_candidates.py` or add `tests/core/excel_target/test_excel_target_candidate_recall.py`:
  - Add matcher-level tests proving the correct rows enter review candidates while automatic matching remains unchanged.
- Modify `tests/cli/commands/test_excel_target_e2e.py` only if an artifact-level regression is needed:
  - Assert JSONL contains the full generated candidate count and saves options with correct source row keys.
- Add `docs/approved-manual-match-learning-20260909/10-before-after-runbook.md`:
  - Record baseline run `20260910_1051`, focused pre-change evidence, exact replay command, and comparison rules.
- Add `docs/approved-manual-match-learning-20260909/11-plan-review.md` after independent review:
  - Record reviewer findings, accepted changes to this plan, and rejected alternatives.

## Task 1: Freeze the failing candidate-recall contract

**Files:**

- Modify: `tests/core/excel_target/test_excel_target_identity_normalization.py`
- Create: `tests/core/excel_target/test_excel_target_candidate_recall.py`

**Interfaces:**

- Consumes: `TargetProduct`, `ExcelTargetBilingualIndex`, `ExcelTargetMatcher`, `MatchingConfig`, `Item`.
- Produces: failing tests for `normalize_arabic_review_brand`, `identify_review_candidates`, and `ExcelTargetMatcher.match(...).review_candidates`.

- [ ] **Step 1: Add normalization tests.**

```python
def test_review_brand_normalization_removes_fused_ampoule_and_status_suffix() -> None:
    assert normalize_arabic_review_brand("فولتارين 3مبول س جديد") == "فولتارين"


def test_review_brand_normalization_removes_fused_tablet_and_status_suffix() -> None:
    assert normalize_arabic_review_brand("زيثرون 3قرص س جديد") == "زيثرون"


def test_review_brand_normalization_does_not_strip_unqualified_brand_suffix() -> None:
    assert normalize_arabic_review_brand("اتور س") == "اتور س"
```

- [ ] **Step 2: Add an isolated bilingual fixture.** Patch `load_tawreed_catalog`, `load_dictionary`, `lookup_en`, and `ar_to_en_many_cached_only` so the fixture contains only audited aliases for `VOLTAREN`/`XITHRONE` and no network work.

```python
VOLTAREN_ALIAS = {"en": "VOLTAREN", "ar": "فولتارين"}
XITHRONE_ALIAS = {"en": "XITHRONE", "ar": "زيثرون"}
```

- [ ] **Step 3: Add the review-only candidate test.** Use rows for the wrong and correct variants, call `matcher.match(Item("vol3", "VOLTAREN 3AMP", 1), MatchingConfig())`, and assert the correct Arabic row is present in `result.review_candidates` with `source_kind == "excel-target"`, `source_file` preserved, and `review_status` explaining compatibility uncertainty/conflict.

- [ ] **Step 4: Assert automatic behavior is not broadened.** The same fixture must assert that the current automatic decision remains `None` when no exact compatible row exists and that `review_identity` is not passed to `_compatible_identified` as an automatic candidate.

- [ ] **Step 5: Run the tests and verify failure before implementation.**

Run:

```powershell
& '.venv\Scripts\python.exe' -m pytest tests\core\excel_target\test_excel_target_identity_normalization.py tests\core\excel_target\test_excel_target_candidate_recall.py -q
```

Expected: FAIL because the review-only normalizer/method does not exist and the correct rows are absent from `review_candidates`.

## Task 2: Implement review-only identity expansion

**Files:**

- Modify: `src/core/excel_target/excel_target_identity.py`
- Modify: `src/core/excel_target/excel_target_matching.py`
- Modify: `src/core/excel_target/excel_target_review_candidates.py`
- Modify: tests from Task 1

**Interfaces:**

- Produces: `normalize_arabic_review_brand(value: str) -> str`.
- Produces: `ExcelTargetBilingualIndex.identify_review_candidates(item_name: str) -> tuple[IdentifiedTarget, ...]`.
- Consumes: the same catalog and audited alias sources already loaded by `ExcelTargetBilingualIndex.build`.

- [ ] **Step 1: Implement the review normalizer as a separate contract.** Do not change the existing automatic `normalize_arabic_brand` output. The review normalizer may remove only documented packaging/status patterns, normalize Arabic digits/diacritics, drop numeric-only tokens, and return whitespace-normalized tokens.

```python
def normalize_arabic_review_brand(value: str) -> str:
    # Normalize Unicode/digits, remove audited variant decorations, remove
    # catalog status markers when an attribute exists, then keep brand tokens.
    ...
```

The implementation must cover `مبول`, `امبول`, `امبولة`, `امبولات`, `قرص`, `اقراص`, `كبسول`, `شراب`, `جل`, dosage units, and the status forms `س جديد`, `س ج`, and `قديم` only when an attribute/decorated product name is present. It must not make a bare `اتور س` equal to `اتور`.

- [ ] **Step 2: Add review alias storage without changing exact maps.** During `ExcelTargetBilingualIndex.build`, keep the current `target_by_arabic`/`by_tawreed_brand` maps intact. Add a first normalized review-token index for all catalog rows. For each Tawreed/dictionary alias that already has at least one exact Arabic target hit, add target rows whose review-normalized tokens begin with the alias's review-normalized tokens. De-duplicate by `_target_identity_key`.

- [ ] **Step 3: Add explicit evidence.** Extend `IdentityKind` with `review_identity` and return:

```python
IdentityEvidence(
    "review_identity",
    brand,
    "review-only anchored Arabic brand expansion",
    0.90,
)
```

This evidence kind must never flow into `_identity_decision` or automatic acceptance.

- [ ] **Step 4: Merge only at review-candidate construction.** In `ExcelTargetMatcher.match`, keep:

```python
identified = self.identity_index.identify(item.name)
accepted, rejected = _compatible_identified(item, identified)
```

and add review-only values only to the evidence passed into `build_review_candidates`:

```python
review_identified = self.identity_index.identify_review_candidates(item.name)
review_evidence = (*identified, *review_identified)
```

Pass `review_evidence` to `build_review_candidates(..., identified=review_evidence, ...)` after de-duplication by row identity.

- [ ] **Step 5: Persist the evidence label.** Map `review_identity` to `candidate_method="review_identity"`; keep `matching_source="excel-target"`, `target_key`, source file, row number, and row key unchanged.

- [ ] **Step 6: Run focused tests.**

Run:

```powershell
& '.venv\Scripts\python.exe' -m pytest tests\core\excel_target\test_excel_target_identity_normalization.py tests\core\excel_target\test_excel_target_candidate_recall.py tests\core\excel_target\test_excel_target_review_candidates.py -q
```

Expected: PASS, including the new correct rows in review candidates and no automatic match caused by `review_identity`.

## Task 3: Validate artifact and UI-facing contracts

**Files:**

- Modify: `tests/cli/commands/test_excel_target_e2e.py` if required by the existing fixture seam
- Modify: `src/cli/commands/cli_order_excel_target.py` only if tests reveal an artifact contract gap
- Create: `docs/approved-manual-match-learning-20260909/10-before-after-runbook.md`

- [ ] **Step 1: Assert candidate counts are not confused with saved counts.** For an item with more options than the configured save limit, assert `candidate_count_total` is the generated total and `candidate_count_saved` is the persisted count. For the two target examples, assert the correct row key is in persisted options under the current limit of 30.

- [ ] **Step 2: Assert source isolation.** Every option in the Excel-target artifact has `matching_source="excel-target"` and the configured target key/source file. No Tawreed candidate payload is allowed to appear in the options list.

- [ ] **Step 3: Assert deterministic ordering.** Run the same matcher twice over the same catalog and compare the ordered tuple of `(row_key, score, candidate_method, review_status, rejection_reason)`.

- [ ] **Step 4: Keep UI display behavior explicit.** The artifact must contain all saved options allowed by configuration. The Streamlit page may display the configured number per page, but it must show the total count and retain pagination/selection access to the remaining options. Do not silently lower the artifact count to the UI limit.

- [ ] **Step 5: Write the runbook.** Record the baseline run `artifacts/order/wardany/20260910_1051`, the historical comparison run `wardany/20260909_1457`, the focused pre-change candidate output, exact command line, after-run directory, and the semantic comparison fields.

## Task 4: Full verification and controlled rollout

- [ ] **Step 1: Run the relevant unit suites.**

```powershell
& '.venv\Scripts\python.exe' -m pytest tests\core\excel_target tests\cli\commands\test_excel_target_e2e.py tests\core\manual_review\test_manual_review_candidates.py -q
```

- [ ] **Step 2: Run the exact user command before/after comparison.** The baseline already completed as `artifacts/order/wardany/20260910_1051`; after implementation run the same command with the same input/config/targets/limit/workers/flags. Record processed/matched/flagged/manual-review totals for Tawreed, Baraka, and Qaysar.

- [ ] **Step 3: Run a focused real-catalog replay for the two examples.** Use `ExcelTargetMatcher` with `use_saved_approvals=False`, `محروس1.xlsx`, and items `VOLTAREN 3AMP`/`XITHRONE 500MG 3TAB`. Compare candidate row keys, names, counts, evidence kinds, and compatibility reasons. The expected after-state contains source rows 3100 and 2345 respectively.

- [ ] **Step 4: Apply acceptance gates.**

```text
correct_row_recall_after == 1.0 for both gold examples
correct_row_recall_after >= correct_row_recall_before
no review_identity automatic match
no candidate source outside the selected Excel target
candidate_count_total >= candidate_count_saved >= 0
candidate row keys are unique and deterministic
```

The primary improvement metric for this request is candidate recall, not automatic match count. Report automatic verified matches separately; a saved manual override is never counted as a new automatic gain.

- [ ] **Step 5: Run static/audit checks and inspect the diff.**

```powershell
& '.venv\Scripts\python.exe' tools\rule_audit.py
git diff --check
git status --short
```

Review that no existing user changes, databases, or workbooks were reverted or staged accidentally.

- [ ] **Step 6: Commit only the feature/docs/tests changes.** Stage explicit paths, use a focused commit message such as `fix: expand Excel manual-review candidate recall`, then push the current feature branch to its configured origin after confirming branch and remote.

## Rejected alternatives

- Raising `manual_review_save_candidate_limit` alone: the correct rows never enter `result.review_candidates`, so a larger writer cap cannot recover them.
- Treating Arabic rows as English fuzzy candidates: this violates the existing bilingual boundary and can introduce unrelated rows.
- Promoting the review-only expansion to automatic matching: this would turn a recall fix into an unreviewed matching-policy change.
- Adding a hard-coded `VOLTAREN`/`XITHRONE` exception: it would solve two rows without improving the general alias/variant path and would be difficult to audit.
