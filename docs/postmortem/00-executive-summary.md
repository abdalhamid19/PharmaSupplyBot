# Postmortem: Excel-Target Run Failure (البركة شركات)

**Date:** 2026-09-05
**Run:** `wardany/20260905_1551`
**Command:** `run.py order --excel data/input/order_items/0000000000006777.xlsx --limit 50 --excel-target "البركة شركات" --match-only ...`
**Outcome:** 🔴 Run hung in a 429 storm for 3+ minutes, produced an **empty summary CSV** (0 bytes), and had to be force-killed. No items were matched.

---

## TL;DR

Three independent failures stacked on top of each other:

1. **The Cohere Trial key is effectively dead** — the monthly quota (1000 calls/month) is exhausted. Headers confirm `x-trial-endpoint-call-remaining: 1`.
2. **The translation cache is NOT being hit by the matcher** — despite 4105 names being pre-translated in `translation_cache`, the bilingual fallback fired thousands of single-name Cohere calls during matching.
3. **No circuit breaker** — on every 429 the code silently fell through to the fallback model (a second failed call), then moved to the next candidate and tried again. Nothing counted consecutive failures or aborted the run.

Result: a run that should take <1 minute offline (cache hits) turned into an unbounded retry storm that burned nothing but time, because every call was rejected.

---

## Impact

| Dimension | Impact |
|---|---|
| Matching quality | Zero — run produced no results |
| Time | ~5 minutes of spinning (killed manually) |
| Cohere quota | No further burn (calls rejected server-side) |
| User trust | Previous runs (20260904_1954_6) had already produced **wrong matches** with nonsense scores (11.00, 12.33 on what should be a 0..1 scale) — confidence in the pipeline is eroded |
| Data | 5 empty CSV artifacts left in `artifacts/excel-target/البركة شركات/` |

---

## Evidence

### A. The quota death certificate

From the run log (15:53:51 onward):

```
x-trial-endpoint-call-limit: 20
x-trial-endpoint-call-remaining: 1
message: "You are using a Trial key, which is limited to
          1000 API calls / month."
```

Two different 429 bodies alternated:
- `limited to 20 API calls / minute` → rate limit (expected, we built a limiter for this)
- `limited to 1000 API calls / month` → **monthly quota exhausted (terminal)**

Our `_RateLimiter` handles the first. It has no concept of the second.

### B. The calls that should never have happened

```
15:52:48  first Cohere call
15:52:51  command-a-translate-08-2025 failed (429)
15:52:55  command-a-plus-05-2026 failed (429)   ← fallback fired anyway
15:52:59  command-a-translate-08-2025 failed    ← next candidate, same story
...
15:55:39  still going (manually killed at ~15:56)
```

Pattern: single-name calls (not batches), two models per name, repeating every ~3.5s. This is `_bilingual_secondary_match` iterating candidates one by one with `ar_to_en(product.name)` per candidate.

**But the DB says the catalog is pre-translated:**

```
sqlite> select count(*) from translation_cache;
4105
```

So every one of these calls is a **cache miss that should have been a hit** → see `01-root-cause-analysis.md` §R2.

### C. Historical data corruption (from run 20260904_1954_6)

| Item | Matched with | Score | Verdict |
|---|---|---|---|
| JACKODAN FACIAL WASH 150ML | اليجا غسول للوجه 150 مل | 11.00 | wrong drug, scale >1 |
| INODEP CAPSULES 30 | سالبوفنت 30قرص | 12.33 | wrong drug (indep vs salbutamol) |
| ACTOS 30 MG 30TAB | سالبوفنت 30قرص | 11.00 | wrong drug (pioglitazone vs salbutamol) |
| BRAYTOFLEX 30 TAB | سالبوفنت 30قرص | 10.39 | third item matched to same product |
| ALFATHROMB 5 MCG 20 TABS | (no-results) | — | correct rejection |

Scores range 5.87 → 90.00 in the same column. A 0..1 scale was intended (`bilingual_min_score=0.7`).

---

## The fix plan

Split across three documents:

| File | Content |
|---|---|
| `01-root-cause-analysis.md` | Deep-dive into each root cause with code paths and line numbers |
| `02-fix-plan.md` | Concrete code changes, ordered by priority, with acceptance criteria |
| `03-operations-guide.md` | Immediate operational workarounds (no code changes) and re-run procedure |

**Do not start implementing until the fix plan is approved.**

---

## Status

- [x] Run executed and captured
- [x] Evidence collected (log, CSVs, DB)
- [x] Root causes identified (R1–R6)
- [x] Fix plan written
- [ ] Fixes approved
- [ ] Fixes implemented
- [ ] Re-run verified
