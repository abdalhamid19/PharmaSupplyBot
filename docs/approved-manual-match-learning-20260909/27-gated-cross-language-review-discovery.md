# Gated Cross-Language Review Discovery

## Purpose

The existing review discovery path can miss a valid Arabic catalog row when
the order item is written in English. This phase adds a bounded recall channel
for that case without allowing the new evidence to create an automatic match.

The channel is intended for cases such as an English brand query and an
Arabic-only target row. It is not a general-purpose translation service and it
does not call a network or live translation provider.

## Safety contract

The channel is review-only:

- cross_language_alias is emitted as a review candidate method.
- It cannot be used by automatic matching.
- Unknown or future review evidence kinds fail closed in automatic matching.
- Existing review-only evidence such as review_identity, review_fuzzy,
  cohere_translation, and cached_cohere remains review-only.
- The feature flag defaults to false, so the production configuration does
  not change until a replay and precision review explicitly approve it.

The matcher still returns no automatic best match when the only evidence is
the cross-language alias. This is covered by an end-to-end matcher test.

## Alias and scope rules

The alias channel uses audited alias entries and optional review aliases. Each
alias is normalized and resolved only against rows already loaded in the
current target catalog.

The implementation applies the following bounded rules:

1. The feature is considered only for an English query.
2. The alias root must contain a meaningful token of at least four characters.
3. Generic-only roots such as CO, COMPANY, GROUP, LAB, MEDICAL, PHARMA, and
   TRADING are rejected.
4. The resolved Arabic brand must match the normalized review brand of the
   target row.
5. Duplicate physical rows are deduplicated by target row key.
6. The existing deterministic limit and ordering remain in force.
7. The alias candidate carries explicit provenance and is ranked in a
   review-only tier.

These rules prevent a short shared prefix or a manufacturer-only suffix from
turning into a broad catalog-wide candidate flood.

## Configuration

The new setting is:

~~~yaml
matching:
  excel_target_review_cross_language_aliases_enabled: false
~~~

The field exists in the typed configuration model, but state/config.yaml has
intentionally not been changed in this phase. Enabling it requires the shadow
replay and acceptance gates in the phase plan.

## Verification completed

The following coverage is now tested:

- English query against an Arabic-only row with an audited alias.
- The cross-language hit is visible as a review candidate and never becomes
  an automatic match.
- The feature is disabled by default.
- Short roots, generic/manufacturer-only roots, and unrelated brands do not
  produce cross-language candidates.
- Existing candidate ranking and cohere-evidence safety behavior remain
  intact.
- Candidate provenance keeps distinct physical target rows separate.

Focused tests passed: 32 passed.

The broader Excel-target and manual-review suite passed:

~~~text
230 passed, 2 subtests passed
~~~

This result is a code-level safety result. It is not a production rollout
approval: the feature flag remains disabled, UI C_display is still an
explicit measurement gate, and the full operational shadow replay with
positive and negative gold cases is still required.

## Subagent review inputs

The rollout review also considered:

- 25-fail-closed-safety-review.md, which confirms fail-closed behavior for
  unknown evidence kinds and identifies the remaining end-to-end safety gate.
- 26-c-display-measurement-design.md, which keeps generated, saved, loaded,
  deduplicated, and displayed candidate counts distinct and requires an
  explicit UI display count.
