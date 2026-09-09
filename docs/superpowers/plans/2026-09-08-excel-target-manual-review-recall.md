# Excel Target Manual-Review Candidate Recall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task with review checkpoints. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase the number of Excel-target items sent to `manual_review` when a plausible target-row candidate exists, while leaving automatic matching safety unchanged.

**Architecture:** Keep the existing verified identity and compatibility pipeline as the only path that can produce `matched`. Add a separate, offline, review-only candidate-discovery index over the already loaded Excel target rows. The discovery layer uses language-specific normalized names, conservative RapidFuzz scoring, brand-token anchors, and explicit variant diagnostics; it never calls Cohere, Tawreed, or any other network provider directly. The surrounding `--match-only` index construction may continue to use the configured Cohere translation provider normally. The existing artifact writer will persist these candidates with provenance so a reviewer can approve or reject them against the exact Excel target.

**Tech Stack:** Python 3.11, dataclasses, RapidFuzz, existing `ExcelTargetMatcher`, `TargetProduct`, SQLite/order-run artifacts, pytest/unittest mocks, PowerShell replay commands.

**Spec:** `docs/superpowers/plans/2026-09-08-excel-target-safe-match-expansion.md`

## Global Constraints

- `matched` may only be produced by the existing verified identity path plus strict variant compatibility or an explicitly scoped approved manual decision.
- Review-only fuzzy candidates must never become `decision.best_match`.
- The review-only layer must use only rows loaded from the requested Excel target; it must not construct candidates from Tawreed rows or dictionaries.
- The review-candidate discovery layer must not call Cohere directly. Existing configured Cohere translation is allowed during normal `--match-only` index construction and must retain batching, cache lookup, rate limiting, monthly quota, and key failover rules.
- Cached Cohere translations remain review-only and must retain their provenance.
- Keep all existing `source_file`, `source_row_number`, and stable target-row identity fields.
- Preserve digit-bearing brand distinctions such as `B12` versus `B6`, and preserve form, concentration, strength, and pack conflicts in review metadata.
- The default per-item saved candidate limit remains the configured `matching.manual_review_save_candidate_limit` (currently 30 in `state/config.yaml`); increasing the number of reviewed items is separate from increasing candidates per item.
- The default discovery result is capped at 5 candidates per item and is deterministic across runs.
- The only coverage categories are `identity_compatible`, `identity_variant_rejected`, `excel_target_candidate_available`, and `identity_absent`.
- Parallel agents, tests, and replays must use isolated temporary SQLite databases, cache copies, and artifact directories; no worker may write the real `state/manual_review_decisions.db`, `state/order_runs.db`, or production cache.
- Existing focused Excel-target, translation, artifact, and safety tests must remain green.
- No real API key may be read, printed, committed, or added to tests; provider interactions are mocked in tests and are allowed only in the user-approved production replay.

---

## Current Baseline and Success Definition

The latest safe replay for 200 items produced:

| Metric | Current value |
|---|---:|
| Excel-target processed | 200 |
| Excel-target matched | 32 |
| Excel-target flagged | 168 |
| Items with `manual_review_required=True` | 41 |
| Flagged items without a saved candidate | 127 |
| Cohere calls during replay | Determined by cache misses and configured batching/rate limits |

The implementation succeeds when every current candidate-bearing item remains present, additional items are added only when the new discovery gates produce at least one target-row candidate, and the automatic `matched` set is unchanged except for previously verified behavior. The plan does not promise an arbitrary count; the count must be derived from measurable candidate evidence.

## Confirmed Variant-Conflict Policy

The user explicitly chose human review for likely same-brand rows even when the
Excel row differs in concentration, dosage form, strength, or pack size. Those
differences are therefore not candidate-removal rules. When the brand identity
gates pass, the row is included in `manual_review` and the exact conflict is
stored as `compatibility_rejection` so the reviewer can decide. Only a missing
meaningful brand anchor, an unrelated name, or an invalid/non-target row removes
the candidate. This policy changes review recall only; it does not relax any
automatic-match rule.

## Confirmed Approved-Correction Override

When a human selects one of these variant-conflict candidates and the
`Saved Corrections (Manual Review Store)` records `manual_decision=
"approved_match"` with `approved=1`, that explicit human decision is allowed
to promote the selected Excel row on later runs even when automatic
compatibility still reports a concentration, form, strength, or pack conflict.
The promotion is not a fuzzy promotion: it is a scoped manual decision.

The saved correction must be bound to the same `excel_target_key` and stable
Excel row identity (`source_file`, `source_row_number`, and stable row key).
The runtime must verify that exactly one current row satisfies that identity.
If the row is absent, duplicated, or the target scope differs, the decision
stays in `manual_review` and records the rebind failure. A legacy approval that
does not contain a target scope or row identity cannot bypass compatibility.
When the scoped approval is applied, the result is marked
`manual_review_rebound` / `approved_manual_override` so reports distinguish it
from an automatic verified match.

## Files and Responsibilities

- Modify `src/core/config/config_models.py` to add explicit review-discovery settings without changing the automatic-match thresholds.
- Modify `state/config.yaml` only to make the conservative review settings explicit for the Baraka replay.
- Create `src/core/excel_target/excel_target_review_discovery.py` for the immutable catalog index, normalization projection, scoring, and safety gates.
- Modify `src/core/excel_target/excel_target_review_candidates.py` to adapt discovery hits into the existing `ExcelTargetReviewCandidate` shape and preserve compatibility metadata.
- Modify `src/core/excel_target/excel_target_matching.py` to invoke discovery only for review candidates and to reuse one matcher per target in multi-target calls.
- Modify `src/cli/commands/cli_order_excel_target.py` to preserve configured Cohere behavior for `--match-only` and persist total versus saved candidate counts.
- Modify `src/core/excel_target/excel_target_identity.py` only if a shared public normalization helper is needed; do not weaken its verified identity rules.
- Modify `src/core/manual_review/manual_review_candidates.py` to deserialize the new review-only evidence fields while remaining compatible with legacy artifacts.
- Modify `src/core/manual_review/manual_review_selection.py`, `src/core/manual_review/manual_review_store.py`, `src/core/manual_review/manual_review_store_sql.py`, and `src/core/manual_review/manual_review_store_helpers.py` to persist and validate the selected Excel row identity for approved corrections.
- Modify `src/ui/manual_review/streamlit_manual_review_page.py` to display review-only score, strategy, shared anchors, and compatibility rejection clearly.
- Modify `scripts/baraka_coverage_report.py` to report candidate availability before and after the review-only layer.
- Add or modify tests under `tests/core/excel_target`, `tests/core/manual_review`, `tests/cli/commands`, and `tests/ui/manual_review` only at public seams.
- Add `docs/baraka_matching_investigation_20260906/10_manual_review_candidate_recall.md` as the replay and operational runbook after implementation.

## Parallel Agent Allocation

Use at least three fresh `gpt-5.6-luna` agents with `xhigh` reasoning after recording `BASE_SHA`. Each agent receives an isolated write set and must use Red → Green → Refactor. No agent may modify another agent's files.

- Agent A: discovery index and scoring — `src/core/excel_target/excel_target_review_discovery.py` and its focused tests.
- Agent B: review-candidate adapter, artifact fields, and manual-review model/UI — `excel_target_review_candidates.py`, `manual_review_candidates.py`, UI file, and their tests.
- Agent B also owns approved-correction row metadata — `manual_review_selection.py`, `manual_review_store.py`, `manual_review_store_sql.py`, `manual_review_store_helpers.py`, and scoped rebind tests; it must not change the automatic discovery scorer.
- Agent C: configuration, coverage report, integration tests, and replay assertions — `config_models.py`, `state/config.yaml`, `baraka_coverage_report.py`, CLI tests, and docs.
- Main integration pass: merge the three diffs, resolve the single public interface, run the complete gates, then dispatch two Luna `xhigh` reviewers for safety and maintainability.

---

### Task 1: Record the baseline and freeze the public seam

**Files:**
- Read: `src/core/excel_target/excel_target_matching.py`
- Read: `src/core/excel_target/excel_target_review_candidates.py`
- Read: `src/cli/commands/cli_order_excel_target.py`
- Read: `scripts/baraka_coverage_report.py`
- Create: `artifacts/excel-target/البركة شركات/<baseline>/manual_review_candidate_baseline.json`

**Interfaces:**
- Consumes: the existing 200-item Baraka `--match-only` artifact.
- Produces: a baseline containing `item_code`, `item_name`, `target_key`, `source_file`, `source_row_number`, `store_product_id`, `status`, `candidate_count_total`, `candidate_count`, `manual_review_required`, `manual_review_category`, `identity_evidence_kind`, and `final_reason`.

- [ ] **Step 1: Record the repository state.**

Run:

```powershell
$baseSha = (git rev-parse HEAD).Trim()
git status --short
Write-Output "BASE_SHA=$baseSha"
```

Expected: the existing dirty files are recorded and not reverted.

- [ ] **Step 2: Generate a stable baseline report from the latest artifact.**

Run:

```powershell
$env:PYTHONUTF8 = "1"
& ".venv\Scripts\python.exe" scripts\baraka_coverage_report.py `
  --config state\config.yaml `
  --excel data\input\order_items\0000000000006777.xlsx `
  --target-key "البركة شركات" `
  --target-path "data\input\excel target\البركة شركات.xlsx" `
  --limit 200 `
  --prevented-items-excel data\input\prevented_items\drugprevented.xlsx `
  --output-prefix "artifacts\excel-target\البركة شركات\baseline\baraka_coverage"
```

Expected: a report that distinguishes identity absence from variant rejection and records current candidate counts.

- [ ] **Step 3: Add the seam contract to the test plan before implementation.**

The public seam is `ExcelTargetMatcher.match(item, matching_config)` and the observable result is `ExcelTargetMatch.review_candidates`. The CLI seam is the generated summary row where `manual_review_required` must equal `candidate_count_total > 0`; `candidate_count` remains the number actually saved after the configured limit.

- [ ] **Step 4: Commit the baseline documentation only.**

```powershell
git add docs/superpowers/plans/2026-09-08-excel-target-manual-review-recall.md
git commit -m "docs: plan safe Excel manual-review recall"
```

---

### Task 2: Add conservative review-discovery configuration

**Files:**
- Modify: `src/core/config/config_models.py`
- Modify: `state/config.yaml`
- Test: `tests/tawreed/order/test_tawreed_checkout.py` or a new `tests/core/config/test_matching_config.py`

**Interfaces:**
- Produces these `MatchingConfig` fields:

```python
excel_target_review_candidates_enabled: bool = True
excel_target_review_candidate_limit: int = 5
excel_target_review_fuzzy_strong_score: float = 90.0
excel_target_review_fuzzy_strong_margin: float = 8.0
excel_target_review_fuzzy_medium_score: float = 86.0
excel_target_review_fuzzy_medium_margin: float = 12.0
excel_target_review_ambiguous_score: float = 88.0
excel_target_review_ambiguous_margin: float = 8.0
```

- [ ] **Step 1: Write a failing configuration test.**

```python
def test_excel_review_discovery_defaults_are_conservative() -> None:
    config = MatchingConfig()
    assert config.excel_target_review_candidates_enabled is True
    assert config.excel_target_review_candidate_limit == 5
    assert config.excel_target_review_fuzzy_strong_score == 90.0
    assert config.excel_target_review_fuzzy_strong_margin == 8.0
    assert config.excel_target_review_fuzzy_medium_score == 86.0
    assert config.excel_target_review_fuzzy_medium_margin == 12.0
    assert config.excel_target_review_ambiguous_score == 88.0
    assert config.excel_target_review_ambiguous_margin == 8.0
```

- [ ] **Step 2: Run the focused test and verify it fails.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\config\test_matching_config.py -q
```

Expected: failure because the fields do not exist yet.

- [ ] **Step 3: Add the fields with exact defaults.**

Add the fields to `MatchingConfig`; do not reuse or alter `high_overlap_threshold`, `medium_score_threshold`, or the automatic-match thresholds. Add the same values under `matching:` in `state/config.yaml` so the production replay is explicit. The strong tier is the initial production gate; the medium tier is enabled only for candidates with a long brand anchor and a unique target row; the ambiguous tier retains the top two for human review and never auto-matches.

- [ ] **Step 4: Run the configuration test and YAML load test.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\config\test_matching_config.py tests\tawreed\order\test_tawreed_checkout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the configuration slice.**

```powershell
git add src/core/config/config_models.py state/config.yaml tests/core/config tests/tawreed/order/test_tawreed_checkout.py
git commit -m "feat: configure Excel review candidate discovery"
```

---

### Task 3: Build the offline review-discovery index

**Files:**
- Create: `src/core/excel_target/excel_target_review_discovery.py`
- Test: `tests/core/excel_target/test_excel_target_review_discovery.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class ReviewDiscoveryConfig:
    enabled: bool = True
    limit: int = 5
    strong_score: float = 90.0
    strong_margin: float = 8.0
    medium_score: float = 86.0
    medium_margin: float = 12.0
    ambiguous_score: float = 88.0
    ambiguous_margin: float = 8.0

@dataclass(frozen=True)
class ReviewDiscoveryHit:
    product: TargetProduct
    score: float
    runner_up_score: float
    score_margin: float
    strategy: Literal["english_fuzzy", "arabic_fuzzy"]
    review_status: Literal["strong", "medium", "ambiguous", "variant_conflict", "variant_unproven"]
    shared_brand_tokens: tuple[str, ...]
    attribute_note: str

@dataclass(frozen=True)
class ExcelTargetReviewDiscoveryIndex:
    @classmethod
    def build(cls, catalog: Sequence[TargetProduct]) -> "ExcelTargetReviewDiscoveryIndex": ...

    def discover(
        self,
        item: Item,
        *,
        config: ReviewDiscoveryConfig,
    ) -> tuple[ReviewDiscoveryHit, ...]: ...
```

- [ ] **Step 1: Write the failing tests for positive and negative discovery.**

```python
def test_typo_with_strong_brand_anchor_returns_review_hit() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build([
        TargetProduct("A", "AMOXICILIN PLUS 30 TABS", 10, 0, source_file="baraka.xlsx")
    ])
    hits = index.discover(
        Item(code="1", name="AMOXICILLIN PLU 30 TABS", qty=1),
        config=ReviewDiscoveryConfig(),
    )
    assert [hit.product.code for hit in hits] == ["A"]
    assert hits[0].strategy == "english_fuzzy"
    assert "AMOXICILLIN" in hits[0].shared_brand_tokens

def test_unrelated_name_has_no_review_hit() -> None:
    index = ExcelTargetReviewDiscoveryIndex.build([
        TargetProduct("A", "AMOXICILIN 30 TABS", 10, 0)
    ])
    hits = index.discover(
        Item(code="1", name="PARACETAMOL 20 TABS", qty=1),
        config=ReviewDiscoveryConfig(),
    )
    assert hits == ()
```

- [ ] **Step 2: Add regression tests for known false-match shapes.**

Cover `B12` versus `B6`, `CO AVAZIR` versus `AVAZIR`, short two-character tokens, a target with a different brand but the same strength, and Arabic spelling/diacritic variants. The expected result for a dangerous near miss is either no hit or a review-only hit with an explicit anchor/modifier note; it must never be an automatic match.

- [ ] **Step 3: Run the discovery tests and verify they fail.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\excel_target\test_excel_target_review_discovery.py -q
```

Expected: failure because the module and index do not exist.

- [ ] **Step 4: Implement the immutable catalog index.**

Index only `TargetProduct` rows loaded from the target workbook. Store separate English and Arabic normalized keys. Use `normalize_english_brand()` and `normalize_arabic_brand()` so digit-bearing identity behavior is shared with verified matching. Keep the stable row identity `(store_product_id, source_file, source_row_number, name)` when deduplicating.

- [ ] **Step 5: Implement the conservative scorer.**

Use `rapidfuzz.fuzz.ratio` or an equivalent sequence scorer; do not use `token_set_ratio` or a containment-only score because those can accept a brand with an extra/missing prefix. Search language-specific buckets only. A hit must satisfy all of these gates:

1. Strong hits score at least `90.0` with a runner-up margin of at least `8.0`.
2. Medium hits score at least `86.0` with a margin of at least `12.0`, have a meaningful brand token of length six or more, and resolve to one target row.
3. Ambiguous hits score at least `88.0`; when the top two are within `8.0`, retain both and mark them `ambiguous`.
4. At least one meaningful shared brand token of length four or more exists, or a single-token edit distance of at most one exists for a token of length six or more.
5. The shared token is not only a dosage, form, unit, pack, route, or generic presentation word.
6. The candidate is a row from the current target catalog and has a stable row identity.
7. The candidate is not already present in the exact identity/diagnostic candidate set.

The ambiguity margin is recorded, not used to force an automatic match. When two variants have scores within `8.0`, retain both up to the configured limit and mark the evidence as ambiguous for the reviewer.

- [ ] **Step 6: Store attribute diagnostics without filtering useful human candidates.**

Run `validate_product_compatibility(item.name, product.name_ar)` for each hit. Keep a hit with a form, strength, concentration, or pack rejection when the brand gates pass; put all detected conflicts in `compatibility_rejection`. A candidate with `compatibility.accepted is False` still increments `candidate_count_total` and still makes `manual_review_required=True`. If attribute extraction cannot prove either side, set `compatibility_status=unknown` / `variant_unproven`; never treat unknown as compatible and never convert a rejected or unknown result into a verified match.

Add explicit tests for all four human-review cases: same brand with a different
concentration, same brand with a different dosage form, same brand with a
different strength, and same brand with a different pack. Each test must assert
that the candidate is persisted, its rejection reason identifies the differing
attribute, and `decision.best_match is None` unless an independent verified
identity path exists.

- [ ] **Step 7: Run the discovery tests and refactor only after green.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\excel_target\test_excel_target_review_discovery.py -q
```

Expected: PASS with deterministic ordering and no network calls.

- [ ] **Step 8: Commit the discovery slice.**

```powershell
git add src/core/excel_target/excel_target_review_discovery.py tests/core/excel_target/test_excel_target_review_discovery.py
git commit -m "feat: discover conservative Excel review candidates"
```

---

### Task 4: Adapt discovery hits to the existing review-candidate contract

**Files:**
- Modify: `src/core/excel_target/excel_target_review_candidates.py`
- Modify: `src/core/excel_target/excel_target_identity.py` only if `review_fuzzy` must be added to the evidence type
- Test: `tests/core/excel_target/test_excel_target_review_candidates.py`

**Interfaces:**

Add optional review metadata to `ExcelTargetReviewCandidate`:

```python
candidate_method: str = ""
score_margin: float = 0.0
shared_brand_tokens: tuple[str, ...] = ()
excel_target_row_key: str = ""
excel_target_source_row: int = 0
```

Extend the builder without changing existing callers:

```python
def build_review_candidates(
    item: Item,
    target_key: str,
    catalog: Sequence[TargetProduct],
    *,
    identified: Iterable[IdentifiedTarget] = (),
    diagnostics: Iterable[CandidateMatchDiagnostic] = (),
    discovery_hits: Iterable[ReviewDiscoveryHit] = (),
    limit: int | None = None,
    catalog_by_id: Mapping[str, TargetProduct] | None = None,
) -> tuple[ExcelTargetReviewCandidate, ...]: ...
```

- [ ] **Step 1: Write a failing adapter test.**

```python
def test_fuzzy_hit_is_review_only_and_keeps_variant_rejection() -> None:
    matcher = ExcelTargetMatcher(
        "baraka",
        [TargetProduct("A", "INODEP SYRUP 100 ML", 42, 5, source_file="baraka.xlsx")],
    )
    result = matcher.match(Item(code="1", name="INODEP CAPSULES 30", qty=1), MatchingConfig())
    candidate = next(c for c in result.review_candidates if c.product.code == "A")
    assert candidate.candidate_method == "english_fuzzy"
    assert candidate.compatibility.accepted is False
    assert "form" in candidate.compatibility_rejection
    assert result.decision.best_match is None
```

- [ ] **Step 2: Implement the adapter.**

Create `IdentityEvidence("review_fuzzy", ...)` only for review metadata. Preserve existing exact evidence order and use a stable key so an exact candidate replaces a fuzzy duplicate. Keep all target-row fields confined to the target product adapter.

- [ ] **Step 3: Add the required evidence fields to `to_review_candidate_dict()`.**

Persist `candidate_method`, `score_margin`, `shared_brand_tokens`, `excel_target_row_key`, `excel_target_source_row`, `identity_evidence_kind`, `identity_evidence`, `compatibility_status`, and `compatibility_rejection`. The source must remain `excel-target`; the strategy belongs in the evidence metadata, not in the supplier identity. Deduplicate by `(target_key, source_file, source_row_number, normalized_name)` rather than `store_product_id` alone.

- [ ] **Step 4: Run the focused adapter tests.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\excel_target\test_excel_target_review_candidates.py tests\core\excel_target\test_baraka_safe_matching.py -q
```

Expected: existing exact-candidate tests and the new fuzzy review-only test pass; all `decision.best_match` assertions for unsafe cases remain `None`, while every brand-qualified variant conflict remains in `review_candidates`.

- [ ] **Step 5: Commit the adapter slice.**

```powershell
git add src/core/excel_target/excel_target_review_candidates.py src/core/excel_target/excel_target_identity.py tests/core/excel_target
git commit -m "feat: persist review-only candidate evidence"
```

---

### Task 5: Integrate discovery without changing automatic matching

**Files:**
- Modify: `src/core/excel_target/excel_target_matching.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`
- Test: `tests/core/excel_target/test_excel_target.py`

**Interfaces:**
- `ExcelTargetMatcher.__init__` builds one `ExcelTargetReviewDiscoveryIndex` from its catalog.
- `ExcelTargetMatcher.match()` passes discovery hits to `build_review_candidates()` only after existing identity and native-English decision logic has run.
- `match_item_against_all_targets()` creates one matcher per target before iterating items.
- `review_fuzzy` is a review-only type that cannot be accepted by `_identity_decision`, `first_accepted_match`, auto-save, or any automatic result serializer.

- [ ] **Step 1: Write failing integration tests.**

```python
def test_review_discovery_cannot_create_best_match() -> None:
    matcher = ExcelTargetMatcher(
        "baraka",
        [TargetProduct("A", "AMOXICILIN PLUS 30 TABS", 10, 0)],
    )
    result = matcher.match(Item(code="1", name="AMOXICILIN PLU 30 TABS", qty=1), MatchingConfig())
    assert result.review_candidates
    assert result.decision.best_match is None

def test_exact_verified_match_still_has_no_review_only_override() -> None:
    matcher = ExcelTargetMatcher(
        "baraka",
        [TargetProduct("A", "INODEP CAPSULES 30", 10, 0)],
    )
    result = matcher.match(Item(code="1", name="INODEP CAPSULES 30", qty=1), MatchingConfig())
    assert result.decision.best_match is not None
    assert result.decision.best_match.data["storeProductId"] == "A"
```

- [ ] **Step 2: Run the tests and verify the new test fails.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\excel_target\test_baraka_safe_matching.py -q
```

Expected: the typo item has no review candidate before integration.

- [ ] **Step 3: Build and reuse the review index once.**

Construct the index in `ExcelTargetMatcher.__init__`. Pass the current discovery fields to `discover()`. Preserve the existing `allow_live_translation` behavior for `--match-only`; Cohere may run during index construction when configured and when names are missing from dictionaries/cache. The review-discovery index itself must never call Cohere, and it must consume only the catalog rows plus already available local identity data. Cohere calls must use the existing batch size, per-key rate limiter, monthly quota/failover behavior, and cache write path. Any explicit pre-translation operation remains a separate optional command, but it is not required for normal `--match-only`.

- [ ] **Step 4: Keep the verified decision branch unchanged.**

Do not pass fuzzy hits to `_compatible_identified()`, `_identity_decision()`, `_native_english_decision()`, or `first_accepted_match()`. Fuzzy hits enter only `review_candidates`. Add explicit runtime guards that reject `review_fuzzy` from `_identity_decision`, auto-save, and automatic result serialization even if a future caller passes the wrong evidence object. The only automatic decision inputs remain native English, dictionary/Tawreed bilingual identity, safe aliases, approved scoped manual decisions, and strict compatibility.

- [ ] **Step 5: Reuse matchers across all targets.**

Change `match_item_against_all_targets()` to:

```python
matchers = {
    target_key: ExcelTargetMatcher(target_key, catalog)
    for target_key, catalog in catalogs.items()
}
return {
    target_key: matcher.match(item, app_config.matching)
    for target_key, matcher in matchers.items()
}
```

This prevents rebuilding the aliases, identity maps, and review index for every item.

- [ ] **Step 6: Run integration tests and inspect automatic-match diffs.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\excel_target tests\cli\commands\test_excel_target_e2e.py -q
```

Expected: all focused tests pass; no new `decision.best_match` or auto-save record comes from `review_fuzzy`.

- [ ] **Step 7: Commit the integration slice.**

```powershell
git add src/core/excel_target/excel_target_matching.py tests/core/excel_target tests/cli/commands/test_excel_target_e2e.py
git commit -m "feat: integrate offline Excel review discovery safely"
```

---

### Task 6: Persist and display review-only provenance

**Files:**
- Modify: `src/core/manual_review/manual_review_candidates.py`
- Modify: `src/ui/manual_review/streamlit_manual_review_page.py`
- Test: `tests/cli/commands/test_excel_target_manual_review_artifacts.py`
- Test: `tests/core/manual_review/test_manual_review_candidates.py`
- Test: `tests/ui/manual_review/test_streamlit_manual_review.py`

**Interfaces:**
- `ReviewCandidateOption.from_dict()` accepts the new optional fields and continues loading legacy JSONL.
- The CLI adds `candidate_count_total` while retaining the backward-compatible `candidate_count` as the number saved after the configured limit.
- The CLI contract becomes `manual_review_required = (candidate_count_total > 0)`; a save limit may reduce displayed options but must not hide that an item has a candidate.
- The UI shows a review-only label and the compatibility rejection without offering it as an automatic result.

- [ ] **Step 1: Write failing artifact tests.**

Assert that a saved candidate contains:

```python
assert option.matching_source == "excel-target"
assert option.identity_evidence_kind == "review_fuzzy"
assert option.candidate_method == "english_fuzzy"
assert option.score_margin >= 0
assert option.compatibility_status in {"compatible", "rejected", "unknown"}
```

Also assert that an old candidate dictionary without these fields still deserializes. Replace the old expectation that an unknown but brand-qualified row has no manual-review entry with a test that a fuzzy target-row candidate is saved, has `candidate_count_total >= 1`, `manual_review_required=True`, `matched=False`, and is not auto-saved.

- [ ] **Step 2: Add optional model fields with legacy-safe defaults.**

Add `candidate_method: str = ""`, `score_margin: float = 0.0`, and `shared_brand_tokens: tuple[str, ...] = ()` to `ReviewCandidateOption`. Normalize missing values in `from_dict()` and do not make any new field required.

- [ ] **Step 3: Update the UI card.**

For `identity_evidence_kind == "review_fuzzy"`, display `Review-only fuzzy candidate`, the score/margin, shared brand tokens, source workbook, row number/key, and `compatibility_rejection`. Use `unknown`/`not_verified` when attribute extraction cannot prove compatibility; never display that state as compatible. Do not render a green verified-match indicator for this evidence kind.

- [ ] **Step 4: Run artifact and UI tests.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\cli\commands\test_excel_target_manual_review_artifacts.py tests\core\manual_review\test_manual_review_candidates.py tests\ui\manual_review\test_streamlit_manual_review.py -q
```

Expected: PASS, including legacy artifact loading.

- [ ] **Step 5: Commit the provenance slice.**

```powershell
git add src/core/manual_review/manual_review_candidates.py src/ui/manual_review/streamlit_manual_review_page.py tests/cli/commands tests/core/manual_review tests/ui/manual_review
git commit -m "feat: expose Excel review candidate provenance"
```

---

### Task 7: Apply scoped approved-match corrections, including variant conflicts

**Files:**
- Modify: `src/core/manual_review/manual_review_store.py`
- Modify: `src/core/manual_review/manual_review_store_sql.py`
- Modify: `src/core/manual_review/manual_review_store_helpers.py`
- Modify: `src/core/manual_review/manual_review_selection.py`
- Modify: `src/core/excel_target/excel_target_loader.py`
- Modify: `src/core/excel_target/excel_target_review_candidates.py`
- Modify: `src/core/excel_target/excel_target_matching.py`
- Test: `tests/core/manual_review/test_manual_review_selection.py`
- Test: `tests/core/manual_review/test_manual_review_store_metadata.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`

**Interfaces:**

Add stable row metadata to the review option and saved decision:

```python
# ReviewCandidateOption and ManualReviewDecision
excel_target_row_key: str = ""
excel_target_source_row: int = 0
```

The row key is generated from `target_key`, normalized `source_file`,
`source_row_number`, `store_product_id`, and normalized product name. Add the
same nullable-safe columns to the SQLite schema and migration statements.
Expose one shared helper with this exact contract so artifact writing and
rebind validation cannot calculate different identities:

```python
def excel_target_row_key(target_key: str, product: TargetProduct) -> str: ...
```

The helper must include the full tuple
`(target_key, normalized_source_file, source_row_number, store_product_id,
normalized_name)` and return a deterministic SHA-256 hex string. Duplicate
codes with different rows therefore remain distinct and cannot be rebound by
code alone.

- [ ] **Step 1: Write failing tests for selecting a conflicting variant.**

Create a review option whose brand is correct but whose concentration or form
differs from the order item. Call `decision_from_selection()` and assert:

```python
assert decision.manual_decision == "approved_match"
assert decision.approved is True
assert decision.excel_target_key == "baraka"
assert decision.excel_target_row_key
assert decision.excel_target_source_row == 17
```

- [ ] **Step 2: Write failing tests for scoped approved rebind.**

Save the decision in a temporary SQLite database, construct the same target row
with the same stable row key, and assert that `_scoped_manual_review()` returns
a match even though `validate_product_compatibility()` rejects the variant.
Assert that the result carries `DecisionSource.MANUAL_REVIEW_SAVED`, evidence
`manual_review_rebound`, and metadata `approved_manual_override`.

- [ ] **Step 3: Write failing tests for invalid scope and stale rows.**

Cover a different `target_key`, a different `source_file`, a different
`source_row_number`, and duplicate current rows. Each case must return no
automatic match, preserve `manual_review`, and record a rebind failure. A
legacy `approved_match` without row identity must not bypass compatibility.

- [ ] **Step 4: Run the tests and verify they fail.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\manual_review\test_manual_review_selection.py tests\core\manual_review\test_manual_review_store_metadata.py tests\core\excel_target\test_baraka_safe_matching.py -q
```

Expected: failure because row identity is not yet saved and incompatible
approved corrections are currently rejected by the Excel rebind path.

- [ ] **Step 5: Persist the row identity.**

Extend the dataclasses, SQL `SELECT`, `UPSERT`, table creation, migration, and
row conversion helpers. When the UI creates `approved_match`, copy the selected
option's target key, source file, source row, and stable row key. Do not change
the meaning of `not_matching` or `needs_correction`.

- [ ] **Step 6: Implement the explicit approval override.**

In `_scoped_manual_review()`, first require `approved=True` and
`manual_decision == "approved_match"`. Resolve exactly one current target row
by stable row key. If the row key is absent, allow only the existing safe
legacy path when target scope and source identity are unique and compatibility
passes; never use a legacy record to override a variant conflict. For a new
scoped row-key approval, allow the saved human choice despite compatibility
rejection and create a rebound decision with:

```text
identity_evidence_kind = manual_review_rebound
compatibility_status = approved_manual_override
compatibility_rejection = original detected conflict
DecisionSource = MANUAL_REVIEW_SAVED
```

The override must remain target-row-specific and must not be reused by another
item, target, source file, or duplicate row.

When the override is returned as a decision, the CLI must count it as a
human-approved match and persist `manual_decision=approved_match`; it must not
reclassify it as an automatic verified identity. A new replay of the same item
must therefore show `matching_source=excel-target`,
`identity_evidence_kind=manual_review_rebound`, and
`compatibility_status=approved_manual_override`.

- [ ] **Step 7: Run the tests and refactor after green.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\manual_review\test_manual_review_selection.py tests\core\manual_review\test_manual_review_store_metadata.py tests\core\excel_target\test_baraka_safe_matching.py -q
```

Expected: PASS, including promotion of an explicitly approved variant
conflict and rejection of stale/ambiguous approvals.

- [ ] **Step 8: Commit the approval slice.**

```powershell
git add src/core/manual_review src/core/excel_target tests/core/manual_review tests/core/excel_target
git commit -m "feat: honor scoped approved Excel variant corrections"
```

---

### Task 8: Add coverage reporting and a no-network guard

**Files:**
- Modify: `scripts/baraka_coverage_report.py`
- Modify: `src/cli/commands/cli_order_excel_target.py`
- Test: `tests/core/excel_target/test_coverage.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`

**Interfaces:**
- Coverage records expose `review_candidate_count_total`, `review_candidate_count_saved`, `review_candidate_methods`, `review_candidate_scores`, and `coverage_category`.
- Categories are exactly `identity_compatible`, `identity_variant_rejected`, `excel_target_candidate_available`, and `identity_absent`.

- [ ] **Step 1: Write failing coverage assertions.**

```python
assert record.review_candidate_count_total == len(match.review_candidates)
assert record.review_candidate_count_saved <= record.review_candidate_count_total
assert record.coverage_category == "excel_target_candidate_available"
assert "review_fuzzy" in record.review_candidate_methods
```

Add tests that patch the Cohere batch boundary and the translation-cache write boundary. Assert that review-candidate discovery makes neither call directly. Add a separate index-construction test that allows the configured Cohere batch path and asserts unresolved names are sent in batches of at most 50, cached names are skipped, results are persisted, and a temporary rate-limit error waits/retries without incorrectly switching keys. The CLI integration test must assert that `--match-only` preserves the configured `allow_live_translation` value instead of forcibly disabling it.

- [ ] **Step 2: Add the fields and category precedence.**

Use this precedence:

1. `identity_compatible` when an automatic verified match exists.
2. `identity_variant_rejected` when identity exists but all variants fail compatibility and no review candidate exists.
3. `excel_target_candidate_available` when `review_candidates` is non-empty and no automatic match exists.
4. `identity_absent` when neither identity nor review candidate exists.

- [ ] **Step 3: Run the report tests.**

```powershell
& ".venv\Scripts\python.exe" -m pytest tests\core\excel_target\test_coverage.py tests\core\excel_target\test_baraka_safe_matching.py -q
```

Expected: PASS; the discovery-only test has zero provider calls, while the mocked index-construction test verifies the permitted Cohere calls and cache writes.

- [ ] **Step 4: Commit the coverage slice.**

```powershell
git add scripts/baraka_coverage_report.py src/cli/commands/cli_order_excel_target.py tests/core/excel_target/test_coverage.py tests/core/excel_target/test_baraka_safe_matching.py
git commit -m "test: report Excel review candidate coverage"
```

---

### Task 9: Run a staged 50-item offline evaluation

**Files:**
- Create: `scripts/evaluate_excel_target.py`
- Create: `tests/core/excel_target/fixtures/gold_labels.csv`
- Create: `tests/core/excel_target/test_excel_target_evaluator.py`
- Create: `artifacts/excel-target/البركة شركات/<run>/review_candidate_diff.json`
- Read: `artifacts/excel-target/البركة شركات/20260908_1700/match_only_summary_البركة شركات.csv`

**Interfaces:**
- Consumes: the same order workbook, target workbook, config, and prevented-items workbook as the production replay.
- Produces: a before/after diff keyed by `(item_code, item_name)`.
- Produces: `matched_set_before`, `matched_set_after`, `new_review_items`, `removed_review_items`, and per-candidate labels without requiring a live provider.

The evaluator command must be:

```powershell
& ".venv\Scripts\python.exe" scripts\evaluate_excel_target.py `
  --before "artifacts\excel-target\البركة شركات\baseline\baraka_coverage.csv" `
  --after "artifacts\excel-target\البركة شركات\candidate-recall-50\baraka_coverage.csv" `
  --output "artifacts\excel-target\البركة شركات\candidate-recall-50\review_candidate_diff.json"
```

The independent fixture `gold_labels.csv` must contain these columns:
`item_code,item_name,target_key,expected_category,expected_store_product_id`.
Seed it with six synthetic cases and explicit expected rows:

| Case | Expected category | Expected automatic product ID |
|---|---|---|
| exact verified match | `identity_compatible` | `exact-1` |
| same brand, different concentration | `excel_target_candidate_available` | empty |
| same brand, different dosage form | `excel_target_candidate_available` | empty |
| same brand, different pack | `excel_target_candidate_available` | empty |
| unrelated brand | `identity_absent` | empty |
| ambiguous two-variant brand | `excel_target_candidate_available` | empty |

The three variant-conflict cases must each contain a saved candidate with the
specific conflict reason; the ambiguous case must retain both target rows.

- [ ] **Step 1: Run the focused 50-item report.**

```powershell
$env:PYTHONUTF8 = "1"
& ".venv\Scripts\python.exe" scripts\baraka_coverage_report.py `
  --config state\config.yaml `
  --excel data\input\order_items\0000000000006777.xlsx `
  --target-key "البركة شركات" `
  --target-path "data\input\excel target\البركة شركات.xlsx" `
  --limit 50 `
  --prevented-items-excel data\input\prevented_items\drugprevented.xlsx `
  --output-prefix "artifacts\excel-target\البركة شركات\candidate-recall-50\baraka_coverage"
```

- [ ] **Step 2: Compare the old and new rows.**

For every newly reviewable item, require `candidate_count_total > 0`, a target source file, a stable row key, `identity_evidence_kind` containing `review_fuzzy` or another existing target evidence, and a non-empty compatibility status including `unknown` when attributes are unproven. For every old candidate-bearing item, require that at least one candidate remains.

- [ ] **Step 3: Verify automatic-match invariants.**

Assert that no automatic matched row has `identity_evidence_kind == review_fuzzy`, no automatic matched row has `compatibility_status == rejected`, and no target candidate has a Tawreed supplier/source label. A row with `identity_evidence_kind == manual_review_rebound` and `compatibility_status == approved_manual_override` is allowed only when it comes from a pre-existing scoped `approved_match` and is reported separately from automatic matches.

- [ ] **Step 4: Label a sample of new candidates.**

Review up to 25 newly added items and record one of `plausible`, `wrong_brand`, `wrong_variant`, or `not_a_candidate` in the diff artifact. The first rollout gate is zero `wrong_brand` candidates promoted automatically; a high `not_a_candidate` rate triggers threshold/index refinement before the 200-item replay.

- [ ] **Step 5: Verify isolated execution.**

Run two evaluator processes in parallel with `TemporaryDirectory()`-backed
SQLite paths and artifact roots. Assert that their candidate JSONL files,
`state` databases, and cache copies are disjoint and that neither process can
alter the production databases. Treat `python -m unittest discover` reporting
zero tests as a failed verification signal; use pytest's explicit test paths
as the acceptance gate.

---

### Task 10: Execute the 200-item match-only replay

**Files:**
- Create: `artifacts/excel-target/البركة شركات/<run>/review_candidate_recall_summary.json`
- Read: `artifacts/order/wardany/<run>/`

- [ ] **Step 1: Run the exact user-approved command.**

```powershell
& 'C:\pc\py\pyreview\PharmaSupplyBot\.venv\Scripts\python.exe' '.\run.py' order --config 'state\config.yaml' --excel 'data\input\order_items\0000000000006777.xlsx' --limit 200 --all-profiles --excel-target 'البركة شركات' --excel-target-path 'البركة شركات=data\input\excel target\البركة شركات.xlsx' --match-only --execution-mode api --item-workers 1 --prevented-items-excel 'data\input\prevented_items\drugprevented.xlsx' --matching-risk-policy safe --flagged-match-action manual-review-only --stop-flag 'artifacts\run-control\order\order_stop.flag'
```

- [ ] **Step 2: Validate count semantics.**

For each target summary row, assert:

```text
manual_review_required == (candidate_count_total > 0)
manual_review_category == excel_target_candidate_available when candidate_count_total > 0
manual_review_category == identity_absent otherwise
```

The total `manual_review` may rise above 41 only through additional candidate-bearing rows, including brand-qualified rows whose form, concentration, strength, or pack is rejected by compatibility. It must never rise because of a non-empty placeholder or a candidate from another source.

- [ ] **Step 3: Validate the safety invariants.**

Check all 200 rows for:

- no `review_fuzzy` automatic match;
- no incompatible automatic match;
- no `cohere_translation` automatic match;
- target source files point to `البركة شركات.xlsx` or the exact configured target source;
- `candidate_count <= 30` under the current configured save limit;
- `candidate_count_total >= candidate_count` and the total count drives `manual_review_required`;
- Any Cohere calls are limited to unresolved names during index construction; each request contains at most 50 names, respects the configured 20 calls/minute and 1000 calls/month limits, skips names already in translation cache, and persists successful translations with provider provenance. The review-discovery step itself contributes zero additional provider calls.

- [ ] **Step 4: Compare to the baseline.**

Report `matched`, `flagged`, `manual_review`, `identity_absent`, `identity_variant_rejected`, `excel_target_candidate_available`, and the number of new candidates by strategy. Report automatic matches, approved manual rebounds, and review-only candidates as separate groups; do not report only the aggregate `manual_review` number.

---

### Task 11: Full verification, review, and rollback gate

**Files:**
- Read: all changed production files since `BASE_SHA`
- Create: `docs/baraka_matching_investigation_20260906/10_manual_review_candidate_recall.md`

- [ ] **Step 1: Run the focused acceptance suite.**

```powershell
$env:PYTHONUTF8 = "1"
& ".venv\Scripts\python.exe" -m pytest `
  tests\core\normalization\test_translation.py `
  tests\core\excel_target `
  tests\core\manual_review `
  tests\cli\commands\test_excel_target_e2e.py `
  tests\cli\commands\test_excel_target_manual_review_artifacts.py `
  tests\ui\manual_review\test_streamlit_manual_review.py -q
```

Expected: all relevant tests pass. Known unrelated repository failures must be listed separately rather than hidden.

- [ ] **Step 2: Run syntax and secret checks.**

```powershell
& ".venv\Scripts\python.exe" -m compileall -q src scripts
git grep -n -I -E "(COHERE_API_KEY|api[_-]?key|token)=[A-Za-z0-9_-]{20,}" -- ':!.env.example' ':!docs/superpowers/plans/*' ':!artifacts/*' || $true
```

Expected: compilation succeeds and no real secret is found. Do not read or print `.env`.

- [ ] **Step 3: Dispatch two independent code reviews.**

Use two `gpt-5.6-luna` agents at `xhigh`: one reviews safety/spec compliance and one reviews performance/maintainability. They must inspect the diff from `BASE_SHA`, especially the separation between `decision.best_match` and `review_candidates`, duplicate target IDs, normalization, and provider boundaries.

- [ ] **Step 4: Resolve critical findings before completion.**

Block completion for any finding that can create an automatic false match, leak a non-target candidate, bypass the configured Cohere batch/rate/quota/cache controls, lose cache provenance, or misreport `manual_review_required`. Performance-only findings may be documented with a measured follow-up if the 200-item replay remains within the accepted runtime.

- [ ] **Step 5: Write the operational runbook.**

Document the exact configuration, replay command, artifact paths, candidate evidence meanings, approval workflow, and rollback rule: disable `excel_target_review_candidates_enabled` if new candidates are noisy, leaving verified matching unchanged.

- [ ] **Step 6: Create the final implementation commit only after all gates pass.**

```powershell
git add src state scripts tests docs/baraka_matching_investigation_20260906/10_manual_review_candidate_recall.md
git commit -m "feat: expand safe Excel manual-review candidates"
```

## Final Acceptance Checklist

- [ ] Existing 41 candidate-bearing items remain candidate-bearing.
- [ ] At least one additional item is added only if the replay discovers a target-row candidate; otherwise the system correctly keeps the count at 41 and reports why.
- [ ] Every added candidate has target provenance, score, strategy, shared anchor, and compatibility status.
- [ ] A brand-qualified candidate with a form, concentration, strength, or pack conflict is still included in `manual_review` with the conflict reason visible to the human reviewer.
- [ ] `manual_review_required` is true exactly when `candidate_count_total > 0`.
- [ ] A saved `approved_match` selected by a human can promote its same scoped Excel row despite a variant conflict, with `manual_review_rebound` and `approved_manual_override` provenance.
- [ ] An approved correction with a different target, source file, source row, duplicate row key, or missing scoped row identity cannot promote a match.
- [ ] Fuzzy review-only candidates cannot produce `matched`.
- [ ] No automatic false-match guard regresses for `B12/B6`, form, concentration, strength, pack, or brand-prefix cases.
- [ ] Cohere remains available during normal `--match-only` index construction, while review discovery itself makes no direct Cohere call.
- [ ] Cohere requests use batches of at most 50, respect 20 calls/minute and 1000 calls/month, skip cached names, and persist provenance for new translations.
- [ ] Existing cache and Cohere provenance behavior remains intact.
- [ ] Candidate results are deterministic and bounded by configuration.
- [ ] Focused tests, syntax checks, secret scan, replay, and two independent reviews are complete.
