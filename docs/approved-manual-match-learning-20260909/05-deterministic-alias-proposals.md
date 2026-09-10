# Deterministic alias and parser proposals

This document is the human-approval queue produced from the read-only
`approved_match` audit. It answers a narrow question:

> Which deterministic identity or parser changes could explain the
> Cohere-only approvals, and which changes are safe enough to evaluate first?

## Safety status

The queue was approved for implementation on 2026-09-10. The deterministic
rules below are now active in the candidate matcher, with the compatibility
and target-row gates still required before an automatic result is returned.
No fuzzy threshold was lowered, and the saved row-scoped approval behavior
remains the only variant-conflict override.

An approval means “implement and test this proposal in a shadow/candidate
matcher.” It does not mean “convert every similar string into an automatic
match.” Every accepted proposal must have both positive gold cases and nearby
negative cases before it can be enabled for production matching.

## Proposed changes that are worth human review first

| ID | Type | Evidence | Proposed scope | Risk | Suggested decision |
|---|---|---|---|---|---|
| P-001 | Audited identity alias | `COGICINE 30 TABS` was approved as `كوجيسين 30 قرص` in both targets. Local Tawreed/dictionary evidence contains `COGICIN` (without the final `E`) mapping to the same Arabic identity. | Treat `COGICINE` as a reviewed spelling variant of `COGICIN`; keep the alias target/catalog scoped and require the same strength/form/pack compatibility checks. | Low–medium: a global typo alias could affect another catalog. | Approve for a shadow test only; production enablement requires the negative cases below. |
| P-002 | Arabic form/unit parser | `CLOSOL 50 ML SPRAY` was approved as `كلوسول سبراى 50مللى`. Tawreed contains the same product as a topical spray, but the current normalization separates `سبراى`/`بخاخ موضعي` and `مللى`/`مل`. | Add explicit, tested synonym handling for spray/form and millilitre spellings; do not erase the product or pack attributes. | Medium: form or pack loss could broaden a match. | Approve only as a parser experiment with form/volume negative cases. |
| P-003 | Legacy-token parser | `REGCOR 10 MG 10 TAB` was approved as `رجكور 10مجم 10قرص`. Tawreed has `REGCOR 10 MG 10 TAB.` with a trailing legacy token `قديم`; the token currently blocks the otherwise compatible identity. | Ignore `قديم` only as a known catalog-status token after extracting the actual strength, form, and pack. Never remove arbitrary words. | Medium: an over-broad stopword could merge old and current products. | Approve with a targeted token list and an explicit “different strength/current row” negative case. |
| P-004 | Strength/form parser | `LACTASE 1000 ORAL DROPS 15 ML` was approved as `لاكتيز 1000 نقط 15 مل`. Current compatibility accepts both the 1000 and 750 target variants, so this is unsafe without stronger parsing. | Normalize `نقط`/`قطره` and retain the numeric strength (`1000`) and volume (`15 ML`) as first-class attributes. | High until the strength conflict is fixed; the current evidence is not safe for automatic promotion. | Approve investigation/tests, not production activation. |
| P-005 | Catalog-suffix parser | `ATOR 20 MG 10 TAB` was approved as `اتور 20مجم10قرص س`. The trailing `س` behaves like catalog metadata; removing it makes the identity/strength comparison line up with local rows. | Strip only a documented trailing catalog suffix in this target/catalog context, then compare 20 mg and 10 tablets normally. | Medium–high: `س` may be meaningful in another product name. | Approve only target-scoped shadow testing and a negative case where `س` is part of the brand. |
| P-006 | Arabic plural/form parser | `ADOLOR 30 MG 3 AMP` was approved as `ادولور 30مجم 3 امبولات`; Tawreed has the singular `امبول`. | Add a controlled singular/plural synonym for ampoule while retaining count, strength, and product form. | Low–medium if the synonym is attribute-aware; unsafe if implemented as free text deletion. | Approve for a focused test set. |
| P-007 | Explicit bilingual alias | `HERO BABY LF MILK` was approved as `لبن هيرو بيبى ال اف`; dictionary evidence has `HERO BABY LF -> هيرو بابي لف ميلك`. | Add a target-scoped, explicit bilingual alias only if the catalog owner confirms that `لبن`/`ميلك`, `بيبى`/`بابي`, and `ال اف`/`لف` are the intended same product. | Medium–high: broad transliteration aliases can merge products. | Require catalog-owner confirmation before any implementation. |

The first six proposals are parser/identity hypotheses supported by local
catalog evidence. P-007 is intentionally held behind a catalog-owner check
because it depends on bilingual word order and transliteration rather than a
single deterministic typo.

## Cases that should remain manual-only for now

These approvals do not currently have enough deterministic local evidence for
a safe alias. They should remain `Cohere-only`/manual review until a catalog
source, product code, or unambiguous parser rule is supplied:

| Source item | Approved target row | Why no automatic proposal yet |
|---|---|---|
| `ARIPIPREX 10MG 30TAB` | `اريبيبركس 10مجم 30 قرص` | Several strengths exist; no independent local identity evidence. |
| `L CARNITINE SYRUP 30 ML` | `ال كارنتين شراب 30مل` | Generic identity and missing manufacturer/strength make a broad alias risky. |
| `ISOPTIN 80MG 30TAB` | `ايسوبتين 80مجم 30قرص` | No local dictionary/Tawreed evidence found. |
| `XARELTO 20 MG 14 TAB` | `زارلتو 20مجم 14قرص` | No local dictionary/Tawreed evidence found. |
| `TRIGASTCARE 120 CAP` | `ترايجاستكير 120 كبسولة` | No local dictionary/Tawreed evidence found. |
| `TOPOPRAZAN 20 MG 14 TAB` | `توبوبرازن 20مجم 14قرص` | No local dictionary/Tawreed evidence found. |
| `ARIPIPREX`, `L CARNITINE`, and the other generic transliterations | same approved rows | An approval alone is not proof that a global transliteration rule is safe. |

## Required negative cases before enabling any proposal

The candidate matcher must demonstrate all of the following:

1. A different strength is rejected (`REGCOR 5 MG`, `LACTASE 750`,
   `ATOR 40/80`, and the other variants present in the workbooks).
2. A different dosage form, pack count, or volume is rejected.
3. The alias does not match an unrelated target or a different catalog row.
4. Removing a parser token does not remove meaningful brand text.
5. A missing/changed catalog fingerprint disables promotion and returns the
   case to review.
6. The approval-disabled counterfactual replay shows an increase only in
   `automatic_verified`, never by counting an existing
   `approved_manual_override` as new recall.

## What I need from the product owner

## Implementation result

The product owner approved all seven proposals. They were implemented with
positive and negative tests:

- `P-001`: exact audited `COGICINE` alias, indexed only when `كوجيسين` exists
  in the current target catalog.
- `P-002`: controlled spray/form and millilitre normalization, including the
  `/ مل` topical spelling.
- `P-003`: `قديم` is ignored only after actual catalog attributes are present.
- `P-004`: drops strength is retained across `ORAL DROPS`, `نقط`, and
  `قطره`; 750 and 1000 variants remain distinct.
- `P-005`: trailing `س` is removed only for an attributed `اتور` name; a bare
  `اتور س` remains distinct.
- `P-006`: ampoule singular/plural forms share an identity key while count
  compatibility remains strict.
- `P-007`: exact bilingual `HERO BABY LF MILK` alias, indexed only when the
  confirmed Arabic row exists in the target catalog.

The previously manual-only items (`ARIPIPREX`, `L CARNITINE`, `ISOPTIN`,
`XARELTO`, `TRIGASTCARE`, and `TOPOPRAZAN`) remain manual-only; “نفذ كله” did
not turn them into unverified transliteration rules.

The approval-disabled report changed from 1 to 11 `automatic_verified`
findings (+10) and reduced `cohere_review_only` from 17 to 9. Existing
`approved_manual_override` findings are reported separately and are not part
of that gain. The exact 100-item operational replay completed successfully
with 100 processed items; its target summaries were 15 matched/85 flagged/1
manual-review for Baraka and 10 matched/90 flagged/7 manual-review for Caesar.
Those operational totals should be compared only with a run using the same
input ordering and Saved Corrections snapshot.
