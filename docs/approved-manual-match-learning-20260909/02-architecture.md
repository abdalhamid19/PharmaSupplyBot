# Proposed Architecture

## Boundaries

```text
ManualReviewStore (saved decisions)
       │ read-only snapshot
       ▼
ApprovedCorrectionAnalyzer ──► ApprovedCorrectionReport JSON/CSV
       │ replays match with approval disabled       │
       │ joins current target row                   ├─► Streamlit audit table
       ▼                                            └─► rule-candidate queue
RootCauseClassifier
       │
       ▼
ExcelTargetMatcher (existing runtime path)
```

Create a pure analysis module, `src/core/excel_target/approved_correction_analysis.py`.
It receives a `ManualReviewStore` snapshot, catalog(s), a matcher factory, and
configuration. It must not open the production SQLite database itself, mutate
decisions, call Cohere, or alter match thresholds. The matcher factory must
construct `ExcelTargetMatcher(..., use_saved_approvals=False)` (or receive an
equivalent injected null decision lookup). The disabled path must not call a
rebind recorder or any store `upsert`.

Suggested public types:

```python
@dataclass(frozen=True)
class ApprovedCorrectionFinding:
    item_code: str
    item_name: str
    target_key: str
    row_key: str
    excel_target_source_file: str
    excel_target_source_row: int
    approval_run_id: str
    catalog_fingerprint: str
    approval_status: Literal["applied", "stale", "invalid"]
    counterfactual_status: str
    root_cause: str
    original_reason: str
    counterfactual_reason: str
    final_reason: str
    compatibility_status: str
    candidate_method: str
    candidate_count_total: int
    decision_source: str
    match_origin: str

@dataclass(frozen=True)
class ApprovedCorrectionReport:
    findings: tuple[ApprovedCorrectionFinding, ...]
    counts_by_root_cause: Mapping[str, int]
    recommendations: tuple[RuleRecommendation, ...]
```

The analyzer builds the current catalog and verifies the approval row key. For
a valid row it calls the ordinary matcher with a dependency-injected
`saved_decision_lookup` that returns `None`; that is the counterfactual. The
classifier turns the resulting decision and saved metadata into one taxonomy
code. A stale approval is reported, not repaired automatically.

The report must separately count `automatic_verified`,
`approved_manual_override`, `saved_auto_matched`, `stale_or_invalid`, and
`approval_outside_current_input`. Add explicit `match_origin` to artifacts;
do not infer it from a human-readable final reason. The catalog fingerprint is
SHA-256 over canonical `(target_key, source_file, source_row, store_product_id,
name_ar, trusted_name_en)` rows in sorted order.

## Recommended operational loop

1. Generate a report from all `approved_match` decisions for each requested
   Excel target.
2. Review top root-cause groups and sample each proposed normalization/alias.
3. Add deterministic aliases or parser fixes only when the group is safe to
   generalize; keep variant conflicts as manual-only.
4. Add gold labels before the change, use TDD, run the evaluator, then run the
   exact production replay.
5. Publish before/after metrics, audit every new automatic match, and retain
   the report artifact next to the run.

## Better practices incorporated

- Treat manual approvals as labeled data, not a training set for unrestricted
  fuzzy matching.
- Preserve immutable provenance (`target_key`, file, row number, row key) and
  record the catalog fingerprint in reports to detect workbook drift.
- Use a shadow/counterfactual report before enabling any new normalizer rule.
- Keep recommendations in a review queue; a human approves each candidate rule
  and its test cases.
- Use a separate test DB and no network calls for all analysis/evaluation.
