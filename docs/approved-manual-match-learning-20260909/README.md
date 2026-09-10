# Approved Manual Matches: Design Record

**Goal:** improve safe *automatic* matching for every Excel target by using
previous `approved_match` decisions as labeled evidence to identify the *real*
reason the matcher did not select the row initially.

This is a planning package; it makes no matching-policy change. Its companion
baseline is the requested 100-item run at `20260909_1826`.

## The key distinction

An approval is diagnostic training evidence, not the success metric and not an
automatic fuzzy rule for other items. The product should:

1. apply a valid, row-scoped approval as `approved_manual_override`;
2. record the original non-match reason and the later approval in an immutable
   learning/audit record; and
3. aggregate that evidence into safe, reviewable improvements (aliases,
   normalization, and attribute parsing), never into an unreviewed relaxation
   of automatic matching; and
4. measure success only as an increase in `automatic_verified` matches with
   no new unsafe automatic decisions. Existing human overrides are reported
   separately and never counted as recall gained by the feature.

## Existing capability and missing capability

The current `ExcelTargetMatcher` already reads a source-scoped saved decision
and, when it contains the exact current `excel_target_row_key`, returns a
`manual_review_rebound` match. It also deliberately permits an approved human
choice to override a form/strength/pack conflict. This is the correct runtime
safety boundary.

What is missing is a first-class answer to: “which saved approvals were used,
what would have rejected them before approval, and which root-cause group should
be improved next?” The feature in this package supplies that observability,
backfill, and controlled improvement loop.

Read [01-evidence-and-root-causes.md](01-evidence-and-root-causes.md) before
[02-architecture.md](02-architecture.md), then execute
[03-implementation-plan.md](03-implementation-plan.md).

The current human-gated proposal queue is in
[05-deterministic-alias-proposals.md](05-deterministic-alias-proposals.md).
