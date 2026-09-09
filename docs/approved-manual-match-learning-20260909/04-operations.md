# Approved-correction audit operations

This page describes how to use the read-only audit shown in **Saved
Corrections (Manual Review Store)**. The report explains why an
`approved_match` was not selected by the Excel-target matcher before a human
approved it. It does not change the matcher and it does not apply rules.

## What the page displays

The page discovers the newest JSON report below
`artifacts/excel-target/<target-key>/` for each Excel target represented in the
saved decisions. When more than one target is available, the operator selects
the target from the list. The page only reads the report and renders:

- summary counts, kept separate for `automatic_verified`,
  `approved_manual_override`, `saved_auto_matched`, and stale/invalid data;
- root-cause counts, such as `identity_absent`, `variant_conflict`,
  `cohere_review_only`, or `native_score_below_threshold`;
- a bounded sample of findings and stale/invalid approvals;
- recommendation evidence and sample item keys.

Only the report fields needed for the audit are sent to the browser. Source
file values are reduced to workbook basenames; arbitrary report metadata (for
example a database path) is not displayed. The view has no **Apply rule** or
equivalent mutation action. Existing Saved Corrections actions (delete and
approval conversion) remain separate and retain their existing confirmation
behavior.

## Human approval checklist

Treat each recommendation as a hypothesis, not as a proposed automatic
decision. Before changing matching behavior:

1. Confirm the report target key and catalog fingerprint match the workbook
   currently under review.
2. Inspect every sample item and representative candidates for brand,
   modifier, form, strength/concentration, pack size, and manufacturer.
3. Review all stale or invalid approvals. Do not use a stale row key as
   evidence for a new alias or normalization rule.
4. For an identity-related group, inspect all candidate aliases and confirm
   the alias is unambiguous within the target catalog. Reject aliases that
   could identify another product or another target.
5. Add gold cases for the accepted examples and explicit negative cases for
   the nearest unsafe alternatives.
6. Implement one deterministic rule at a time. Do not promote fuzzy,
   Cohere-only, or compatibility-rejected evidence automatically.
7. Run unit tests and the offline shadow/counterfactual evaluation with saved
   approvals disabled. Confirm there are no safety errors and that existing
   gold cases still pass.
8. Run the same input through the candidate matcher and audit every new
   automatic row manually for the attributes in step 2.
9. Publish the before/after comparison. Count only
   `automatic_verified_after - automatic_verified_before` as improvement;
   report `approved_manual_override` separately.

## Report retention and drift

Keep the JSON and UTF-8-SIG CSV report next to the run artifact that produced
it. Do not overwrite a prior report. A changed catalog fingerprint means the
approval was observed against a different workbook snapshot; regenerate the
report before drawing conclusions. A missing or unreadable report should be
treated as an observability gap, not as evidence that matching improved.

## Rollback and incident handling

If a new deterministic rule produces an unsafe automatic match, disable the
rule, preserve the report and comparison artifacts, and restore the previous
matching configuration. Existing row-scoped `approved_match` decisions may
continue to serve as exact manual overrides, but must never be converted into
a broad automatic rule during incident response.

