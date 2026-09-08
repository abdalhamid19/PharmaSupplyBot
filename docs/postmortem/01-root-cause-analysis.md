# Root Cause Analysis — البركة شركات Run Failure

Run: `wardany/20260905_1551` (2026-09-05, killed manually)
Related historical bad run: `20260904_1954_6` (wrong matches, broken scores)

---

## Call graph (what actually executes per item)

```
find_best_match_in_target()                          excel_target_matching.py:226
├─ explain_best_product_match()          (EN↔AR main engine → usually fails, EN name vs AR catalog)
└─ _bilingual_secondary_match()                       :82
   ├─ LOOP over 4105 catalog rows                     :114
   │   ├─ _dict_score()                    (free)
   │   ├─ _ar_brand_to_latin() pre-filter  (free)     :134
   │   └─ match_brand(item_name, product.name)        :147   ← ★ BUG A: full 4-tier scoring as a "trace"
   │        └─ tier 3/4: ar_to_en(ar_row)  → Cohere (LIVE!)
   ├─ top-30 candidates                               :157
   │   ├─ ar_to_en(product.name)                      :164   ← translation path
   │   └─ match_brand(item_name, product.name)        :175   ← ★ BUG A again (second live call per candidate)
   └─ _finalize_fallback()                            :180
        └─ score * 100                                :191   ← ★ BUG C: scale mixing
```

---

## R1 — Cohere Trial quota is exhausted (terminal, not a rate-limit problem)

**Evidence (from run log, 15:53:51+):**

```
x-trial-endpoint-call-limit: 20
x-trial-endpoint-call-remaining: 1
"limited to 1000 API calls / month"
```

Two distinct 429 bodies alternate in the log:
- `20 API calls / minute` → per-minute limit. Our `_RateLimiter` (translation.py:80-99) is designed for this.
- `1000 API calls / month` → **monthly quota gone. Terminal condition.**

**Why the limiter didn't help:** `_RateLimiter` (translation.py:80-102) paces calls at 15/min. It paces *into* a dead quota — every paced call still returns 429. It has no concept of "quota exhausted, stop entirely".

**Consequence:** every translation request in the run fails. There is no code path that says "the API is dead, stop calling it and degrade to offline mode."

---

## R2 — Why does the matcher hit Cohere at all when `translation_cache` holds 4105 entries?

The pre-translate session seeded the cache:

```
translated: 4105 in 574.3s → cache now holds 4105 entries
```

Yet the run fired thousands of single-name calls. Candidate explanations, ordered by likelihood:

### R2a — The "trace" calls bypass the intended translation flow (★ primary suspect)

`excel_target_matching.py:147` and `:175` call `match_brand(item_name, product.name)` **solely to emit a per-tier trace**. But `match_brand` is not a passive tracer — it *executes all four tiers*, including:

- Tier 3: translation-cache lookup (`bilingual_brand_matcher.py:267`)
- Tier 4: **live Cohere translation** (`bilingual_brand_matcher.py:268`)

And `_translation_score` inside it calls `ar_to_en(ar_row)` (bilingual_brand_matcher.py:234). So each "trace" invocation for a cache-miss row = 1 primary Cohere call + 1 fallback Cohere call on failure. With 30 candidates per item × 2 call sites per item, one item can spend ~120 Cohere calls. Multiply by 50 items → thousands of doomed calls.

### R2b — Key-shape mismatch between seeder and runtime lookups

- Seeder (`seed_tawreed_to_cache.py`) wrote keys via `normalize_key()` — which **dedupes and orders tokens** (translation_cache.py:70-77).
- Runtime single lookup (`translation.py:243-245`) does `cache.get_many([cleaned])` then indexes the result by `normalize_key_for_lru(cleaned)` — same normalize, so this *should* hit.

The residual misses are the **143 names the seeder couldn't resolve** at cutoff 80 plus any names whose cleaned form differs (e.g. `س ج` suffixes, double spaces). Those legitimate misses are the ones that *should* go to Cohere — but in a batch, not per-candidate.

**Verification needed (cheap):** pick one name from the 429 storm window and run:

```bash
python -c "
from src.core.database.translation_cache import TranslationCache, normalize_key
tc = TranslationCache()
print(normalize_key('كونكور 5مجم 30قرص س ج'))
print(tc.get_many(['كونكور 5مجم 30قرص س ج']))
"
```

If the dict is empty for a name that appears in `translation_cache`, we have a key-shape bug; if present, R2a is the whole story.

---

## R3 — No circuit breaker on provider failure

`translation.py:234-256` (`_lru_translate`):

```python
primary = _call_cohere(PRIMARY_MODEL, cleaned)     # 429 → None
if primary is None:
    primary = _call_cohere(FALLBACK_MODEL, cleaned) # second doomed call
...
return primary or cleaned                          # returns the ARABIC text as "translation"
```

Failures are swallowed and the caller gets the **Arabic input back as its own translation**. No counter, no abort, no backoff on 429. The caller (`excel_target_matching.py:166`) only checks `translated == product.name` — whitespace-cleaning means the returned Arabic often differs slightly from the raw input, so the failure slips through and is scored.

---

## R4 — Double-call pattern per failed name

On every 429 the code tries primary → fallback. Both fail → one name costs 2 doomed calls. With 15/min pacing, a single name takes ~8s of wall-clock to fail twice. This is exactly the observed ~3.5s cadence per WARNING pair.

---

## R5 — Score scale is broken (historical bad CSV)

`_finalize_fallback` (excel_target_matching.py:191):

```python
score=score * 100,
```

The bilingual path computes scores in `[0.0, 1.0]` (`min_score=0.7`), then multiplies by 100 for the `SearchMatch`. But the CSV recorded scores like `11.00`, `12.33`, `90.00` — a mix of:

- dictionary-path scores × compatibility (e.g. `0.9 × 1.0 → written as 9? or 90?`)
- translation scores in raw 0..1 or ×100

Observed range 5.87–90.00 in one column proves at least two scales are being mixed. The threshold gate `score >= min_score` happens *before* the ×100, so the acceptance logic itself is 0..1 — but everything downstream (CSV, run DB, reconciliation) sees an inconsistent number.

---

## R6 — Wrong matches accepted (quality bug, independent of R1)

From run `20260904_1954_6`:

| Item (EN) | Matched (AR) | Why it's wrong |
|---|---|---|
| JACKODAN FACIAL WASH | اليجا غسول للوجه | both are "facial wash 150ml" — form+pack overlap, brands unrelated |
| ACTOS 30MG 30TAB | سالبوفنت 30قرص | pack "30" + shared form tokens; brand similarity ~0 |
| BRAYTOFLEX 30 TAB | سالبوفنت 30قرص | same product matched to 3 different items |

Mechanism: the pre-filter (`shared chars >= 2` + `quick >= 0.3`) passes almost every catalog row — any two drug names share ≥2 Latin letters after transliteration. Then `_translation_score` on a *garbage/failed* translation (R3 returns Arabic-as-English) or a weak brand match still clears `min_score=0.7` when combined with `_compatibility_factor` ≈ 0.9–1.0 (form+strength+pack often match across unrelated drugs: "30 TAB" is everywhere).

The same wrong product (`سالبوفنت 30قرص`) winning three unrelated items is the smoking gun: the tie-breaking is *not brand-driven* — it's noise reaching the threshold.

---

## R7 — Empty CSV artifacts on interrupted runs (minor)

`run_excel_target_match_only` opens the CSV (`target_summary.open("w")`) *before* the item loop. A run killed mid-loop leaves a 0-byte file. Five such files exist. Cosmetic, but they confuse postmortem reading (newest non-empty CSV is actually 20260904_1954_6, not today's run).

---

## Root-cause summary table

| ID | Cause | Type | Severity | Fix doc |
|---|---|---|---|---|
| R1 | Cohere Trial monthly quota exhausted (remaining: 1) | Operational | 🔴 Blocker | 03 (ops) + 02 (breaker) |
| R2a | `match_brand` used as "trace" fires live Cohere per candidate | Code bug | 🔴 Critical | 02 §F2 |
| R2b | Possible key-shape mismatch seeder↔runtime (needs verification) | Code bug? | 🔴 Critical | 02 §F3 |
| R3 | No circuit breaker / no 429-aware degradation | Code gap | 🔴 Critical | 02 §F1 |
| R4 | Primary→fallback double-call on doomed names | Code gap | 🟠 High | 02 §F1 |
| R5 | Score scale mixing (0..1 vs ×100 vs ×1000) | Code bug | 🟠 High | 02 §F4 |
| R6 | min_score=0.7 + weak compat factor accepts wrong drugs | Quality bug | 🟠 High | 02 §F5 |
| R7 | 0-byte CSVs on killed runs | Cosmetic | 🟢 Low | 02 §F6 |
