# Latest Run Audit 20260514_2107

## Run Summary

- Source run: `artifacts/order/wardany/20260514_2107`.
- Total rows: 50.
- Final statuses: 30 `matched-only`, 20 `manual-review-required`.
- Manual-review rows by final action: 29 `manual_review`, 21 `matched-only`.
- Manual-review AI statuses: 19 `ai_rejected`, 6 `ai_review_rejected`,
  4 `ai_low_confidence`.

## False-Negative Candidates

These rows had strong or exact candidate evidence but were blocked by AI, local
safety, missing orderable ids, or conservative acceptance rules:

- `91733` CHEMICETRIZINE 5 MG20 TAB: Arabic exact DOM match, AI rejected.
- `TOUX` TOUX PROSPERITY SYRUP 120 ML: Arabic exact DOM match, AI rejected.
- `54472` DIVIDO 75 MG 30 TAB: Arabic exact DOM match, AI rejected.
- `27457` EPOETIN 4000 IU VIAL: Arabic exact DOM match, AI rejected.
- `71903` NACTALIA 2 MILK 400 G: Arabic exact DOM match, AI rejected.
- `1587` E-MOX 500MG CAP: high-overlap candidate but pack count concern.
- `89588` REXODIN 10% ANTISEPTIC SOLUTION 60 ML: low AI confidence.
- `91304` panthenol 5% care cream 50 gm: concentration omission concern.
- `adw` ADWIFLAM 6 AMP: strong score but extra numeric strength.
- `19056` ZOVIRAX 10% CREAM: strong score but numeric/concentration mismatch.
- `lev` LEVIASILLS SOOTHING EFFECTIVE RELIEF: Arabic exact candidate.
- `46822` CRYPTONAZ SUSP: strong score but unrequested numeric detail.

## AI/API Problems

- API attempts had 36 rate limits: 25 `groq` 429 and 11 `openrouter` 429.
- API attempts had 5 `opencode` invalid JSON responses.
- AI rejection sometimes hid useful deterministic evidence; artifacts now expose
  deterministic match vs final actionable match separately.
- Review-model rejection remains intentionally blocking unless aggressive mode is
  explicitly enabled and the flagged action allows cart insertion.

## Matching/Trace Problems

- Matching trace was 5069 rows for 50 items, mostly from repeated rejected
  candidates and identity-token failures.
- Top reason groups: `english_name_missing_requested_identity_token`, `rejected`,
  Arabic ML marker checks, unrequested numeric tokens, component mismatch, and
  missing orderable `storeProductId`.
- Candidate-level trace rows are now bounded to keep large runs scalable.

## Implemented Remediation

- Added structured manual-review reason fields to order artifacts.
- Split deterministic match discovery from final actionable match status.
- Added `safe` and `aggressive` matching risk policies.
- Added saved `not_matching` manual-review decisions and runtime filtering.
- Added CLI/GUI removal paths for saved not-matching manual-review rows.
- Bounded matching trace candidate rows to reduce artifact size and UI load.
