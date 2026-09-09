# Excel Target Safe Match Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` and TDD to implement this plan task-by-task. Dispatch multiple `gpt-5.6-luna` subagents with `xhigh` reasoning and disjoint write sets; review every returned patch before integration.

**Goal:** Increase automatic `matched` results for Excel target `البركة شركات` while preserving near-zero false matches and keeping uncertain candidates in manual review.

**Architecture:** Repair target-row identity and variant parsing before adding a conservative alias resolver. Automatic acceptance remains source-aware and requires a unique target row plus strict product-attribute compatibility; Cohere evidence remains review-only under the `safe` policy. A read-only evaluator and labeled gold set gate every recall change.

**Tech Stack:** Python 3.11, openpyxl, RapidFuzz, SQLite, pytest/unittest, Cohere translation API.

**Spec:** This plan incorporates the approved policy that only automatic safe matches count as `matched`, and candidates with missing attributes remain manual-review-only.

## Global Constraints

- Preserve all existing uncommitted user changes; record `BASE_SHA` and inspect overlapping diffs before editing.
- Never read or print `.env`; tests must mock Cohere and must not make network calls.
- Never auto-accept fuzzy similarity alone, an Arabic-only row without corroborated identity, or Cohere-only evidence under `matching-risk-policy=safe`.
- Every explicit query strength, concentration, form, and pack must be proven by the target row.
- A match is automatic only when one compatible target row remains; ambiguity is manual review.
- Do not lower existing shared matching thresholds globally.

---

### Task 1: Establish a Read-Only Evaluation Baseline

**Files:**
- Create: `scripts/evaluate_excel_target.py`
- Create: `tests/core/excel_target/fixtures/gold_labels.csv`
- Test: `tests/core/excel_target/test_excel_target_evaluator.py`

**Interfaces:**
- Produces: `evaluate_excel_target(items_path, target_path, labels_path, limit, cache_snapshot) -> EvaluationReport`.
- `EvaluationReport` exposes `tp`, `fp`, `fn`, `tn`, `precision`, `recall`, `matched`, `manual_review`, and counts by evidence/rejection reason.

- [ ] Write failing tests proving evaluation performs no Cohere calls and does not change hashes of production SQLite/state files.
- [ ] Add labeled cases from the first 200 order rows, including correct match, wrong variant, expected no-match, and manual review.
- [ ] Implement pure evaluation with injected immutable cache and manual-review adapters.
- [ ] Run the evaluator tests and record the current baseline: 32 strict identity-compatible rows from the static inspection; distinguish this from full CLI results affected by saved decisions.
- [ ] Commit the evaluator and fixtures independently.

### Task 2: Stabilize Target Row Identity

**Files:**
- Modify: `src/core/excel_target/excel_target_loader.py`
- Modify: `src/core/excel_target/excel_target_identity.py`
- Test: `tests/core/excel_target/test_excel_target.py`

**Interfaces:**
- Add `source_row_number: int` to `TargetProduct`.
- Make `store_product_id` deterministic: explicit code first; otherwise SHA-256 of normalized source file, row number, and raw name.
- Key identified results by stable target identity, never by possibly empty `product.code`.

- [ ] Write failing tests for multiple code-less variants, duplicate codes, repeated process construction, and identical names from different source files.
- [ ] Implement deterministic IDs and preserve every candidate through compatibility filtering.
- [ ] Add a compatibility rebind path for old manual-review records without allowing an old unstable ID to force a match.
- [ ] Verify exactly one compatible row can match and duplicates remain ambiguous.
- [ ] Commit the identity repair separately before recall changes.

### Task 3: Parse Complete Product Variants

**Files:**
- Modify: `src/core/excel_target/product_attributes.py`
- Test: `tests/core/excel_target/test_product_attributes.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`

**Interfaces:**
- Extend `ProductAttributes` with structured `concentrations` that preserve numerator/denominator relationships.
- Keep `validate_product_compatibility(query, candidate) -> CompatibilityResult` as the public gate.

- [ ] Write failing cases for `228/5 MG`, `250MG/5ML`, `5/12.5/40 MG`, reordered combination strengths, Arabic units, and decimal values.
- [ ] Add distinct non-conflating forms for suspension, solution, lotion, vial, ampoule, suppository, lozenge, and powder.
- [ ] Implement concentration comparison without flattening compound strengths into a permissive set intersection.
- [ ] Preserve negative tests for wrong strength/form/pack, missing injection strength, and unrequested candidate strength.
- [ ] Run evaluator and require zero new false positives before committing.

### Task 4: Add Audited Deterministic Normalization

**Files:**
- Modify: `src/core/excel_target/excel_target_identity.py`
- Test: `tests/core/excel_target/test_excel_target.py`

**Interfaces:**
- Add secondary canonical keys for audited OCR/unit/form spelling variants while preserving the original exact key.

- [ ] Test `MGC/MCG`, `FLIM/FILM`, `SYP/SYRP/SYRUP`, punctuation, whitespace, Arabic digits, diacritics, tatweel, Alef variants, and final Ya.
- [ ] Add collision tests proving `B12 != B`, `MEN != WOMEN`, and that `PLUS`, `DUO`, `TRIO`, `FORTE`, `NIGHT`, and `XR` remain meaningful.
- [ ] Implement only mappings already proven by tests; do not add broad Arabic phonetic substitutions.
- [ ] Run the gold evaluator and commit only if precision remains 100% on labeled automatic decisions.

### Task 5: Implement the Conservative Alias Resolver

**Files:**
- Create: `src/core/excel_target/excel_target_aliases.py`
- Modify: `src/core/excel_target/excel_target_identity.py`
- Test: `tests/core/excel_target/test_excel_target_aliases.py`

**Interfaces:**
- Add `AliasCandidate(product_id, canonical_brand, source, score, runner_up_margin)`.
- Add `ExcelTargetAliasResolver.resolve(item_name: str) -> tuple[AliasCandidate, ...]`.

- [ ] Generate candidates only from local Tawreed and Egyptian dictionary aliases that map back to real target rows.
- [ ] Score brand core while requiring exact equality of meaningful modifiers and digit-bearing tokens.
- [ ] Calibrate the threshold on the gold set; enforce a hard floor of 96 and runner-up margin of 4 regardless of calibration.
- [ ] Pass candidates through full variant compatibility and require one surviving stable target ID.
- [ ] Route threshold failures, collisions, and multiple survivors to manual review with explicit evidence and reasons.
- [ ] Test adversarial pairs including `CENTRUM MEN/WOMEN`, similarly spelled unrelated brands, wrong combination strengths, and equal-score candidates.
- [ ] Run evaluator; accept the task only with zero labeled FP and a measurable recall gain.

### Task 6: Make Acceptance Source-Aware

**Files:**
- Modify: `src/core/excel_target/excel_target_matching.py`
- Modify: `src/cli/commands/cli_order_excel_target.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`
- Test: `tests/cli/commands/test_excel_target_e2e.py`

**Interfaces:**
- Add an explicit acceptance policy keyed by `IdentityEvidence.kind`; confidence numbers alone never authorize automatic matching.

- [ ] Permit automatic matching for native, exact Tawreed, exact dictionary, audited cache, and safe deterministic aliases only after uniqueness and compatibility gates.
- [ ] Make `cohere_translation` manual-review-only under `safe`, even when its translated key is exact.
- [ ] Collect all accepted targets before selection and return ambiguity if multiple target workbooks match without configured priority.
- [ ] Prove manual-review results are excluded from the `matched` metric and are never auto-saved as accepted orders.
- [ ] Commit the policy and CLI integration together.

### Task 7: Preserve Cohere Budget and Cache Guarantees

**Files:**
- Modify only if tests expose a gap: `src/core/normalization/translation.py`
- Test: `tests/core/normalization/test_translation.py`

**Interfaces:**
- Preserve two-key failover, legacy key compatibility, batch size 50, per-key 20 calls/minute, and SQLite cache behavior.

- [ ] Verify 50 names use one call and 51 use two calls.
- [ ] Verify dictionary/Tawreed/cache-resolved rows cause zero calls.
- [ ] Verify quota/billing/invalid-key failures move to the second key while temporary rate limiting waits on the same key.
- [ ] Verify both exhausted keys return unresolved results safely.
- [ ] Verify the second run sends no calls for cached names.

### Task 8: Parallel Review and Final Verification

**Agent execution contract:**
- Use at least three concurrent `gpt-5.6-luna` subagents with `reasoning_effort="xhigh"`.
- Assign disjoint write sets: identity, attributes/aliases, and evaluator/security.
- Use fresh Luna reviewers for standards and spec review after integration.
- The main agent owns interface integration, resolves overlaps, and reviews every diff.

- [ ] Run focused pytest suites for translation, identity, aliases, attributes, safe matching, evaluator, and CLI integration.
- [ ] Run `python -m unittest discover` because repository CI uses unittest discovery.
- [ ] Run clean-code and security review; scan tracked files for secrets without displaying secret values.
- [ ] Run the read-only evaluator and inspect every newly automatic match manually before the production command.
- [ ] Require no regression in existing correct matches, zero labeled false positives, and strict provenance for every new automatic match.

### Task 9: Run the Requested 200-Item Command

- [ ] Verify all input paths and inspect whether the stop flag exists; do not delete it automatically.
- [ ] If the stop flag is absent, execute exactly:

```powershell
& 'C:\pc\py\pyreview\PharmaSupplyBot\.venv\Scripts\python.exe' `
  '.\run.py' order `
  --config 'state\config.yaml' `
  --excel 'data\input\order_items\0000000000006777.xlsx' `
  --limit 200 `
  --all-profiles `
  --excel-target 'البركة شركات' `
  --excel-target-path 'البركة شركات=data\input\excel target\البركة شركات.xlsx' `
  --match-only `
  --execution-mode api `
  --item-workers 1 `
  --prevented-items-excel 'data\input\prevented_items\drugprevented.xlsx' `
  --matching-risk-policy safe `
  --flagged-match-action manual-review-only `
  --stop-flag 'artifacts\run-control\order\order_stop.flag'
```

- [ ] Compare final `matched`, `manual-review`, and `no-results` against the 200-item baseline and group gains by evidence kind.
- [ ] Audit every newly matched row for brand, modifier, form, complete strength/concentration, and pack compatibility.
- [ ] Report Cohere call count/cache additions without exposing keys, and identify any remaining high-value manual-review groups.
