# Independent Plan Review and Incorporated Improvements

An independent Luna `xhigh` review examined the matcher, artifacts, and manual
review store before this document was finalized.

## Confirmed findings

- There are 140 Excel-target `approved_match` decisions: 85 for البركة شركات,
  54 for القيصر شركات, and one legacy `baraka` target.
- In the earlier 100-row target run, 11 Baraka and 9 Caesar results were
  approved overrides. The dominant original causes were strength/form/pack
  conflicts and Cohere-only identity, not generally low matching scores.
- `ExcelTargetMatcher` already applies a valid exact-row approval as
  `manual_review_rebound` with `approved_manual_override`.

## Review changes applied

1. The plan now requires an explicit approval-disabled matcher seam. Without
   it, replay would read the same approval and produce a misleading result.
2. Analysis is read-only: neither stale nor valid approvals may trigger a
   store rebind/upsert during a report.
3. Findings include full row/run provenance, catalog fingerprint, both reasons,
   candidate count, decision source, and explicit match origin.
4. Metrics distinguish automatic verified results, human overrides, saved
   auto-matches, stale/invalid approvals, and approvals outside input scope.
5. Rollout requires an approval-disabled counterfactual baseline as well as
   the production baseline.

## Remaining recommendation

Deliver the analyzer/report first with no policy change. In a later release,
adopt only human-approved deterministic aliases or parser fixes backed by gold
cases. Variant conflicts and Cohere-only evidence remain manual-only.
