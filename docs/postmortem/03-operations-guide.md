# Operations Guide — Running البركة شركات Until Fixes Land

This is the *no-code-changes* playbook. Everything here works around the current codebase as-is. For permanent fixes see `02-fix-plan.md`.

---

## 1. Current state of the Cohere Trial key

| Fact | Value |
|---|---|
| Per-minute limit | 20 calls (our limiter: 15/min ✓) |
| **Monthly quota** | **1000 calls — EXHAUSTED** (`x-trial-endpoint-call-remaining: 1` as of 2026-09-05 15:53) |
| Reset | Start of next calendar month (check dashboard: https://dashboard.cohere.com/api-keys) |

**Consequence:** until the quota resets or you upgrade to a Production key, **any** translation attempt that misses the cache will fail with 429. Do not run matching workloads that expect live translation.

## 2. Cache state (the good news)

`state/order_runs.db → translation_cache` holds **4105 translations** for the البركة شركات catalog (seeded 2026-09-04/05). Most catalog names resolve offline. The 143 seeder misses + any normalization variants are the only ones needing live calls.

Check any name offline:

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "
from src.core.database.translation_cache import TranslationCache
tc = TranslationCache()
print(tc.get_many(['<Arabic name here>']))
"
```

Cache stats:

```powershell
python -c "
import sqlite3
c = sqlite3.connect(r'state\order_runs.db')
print(c.execute('select count(*), sum(hits) from translation_cache').fetchone())
"
```

## 3. Safe runbook until fixes land

### 3.1 Run with a TINY limit first

```powershell
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe run.py order --config state\config.yaml `
  --excel data\input\order_items\0000000000006777.xlsx `
  --limit 3 --all-profiles `
  --excel-target "البركة شركات" `
  --excel-target-path "البركة شركات=data\input\excel target\البركة شركات.xlsx" `
  --match-only --execution-mode api --item-workers 1 `
  --prevented-items-excel data\input\prevented_items\drugprevented.xlsx `
  --matching-risk-policy safe `
  --flagged-match-action manual-review-only `
  --stop-flag artifacts\run-control\order\order_stop.flag
```

Watch the first minute. **If you see any `429` warning pair → the run will not converge. Kill it** (Ctrl+C) — it will spin per-candidate for many minutes otherwise.

### 3.2 The kill criterion (memorize this)

- ✅ Safe to let run: log shows `match_only_summary` rows being written, no httpx/cohere lines.
- 🚨 Kill immediately: 2+ consecutive `WARNING | cohere ... failed ... 429` lines. Each warning pair costs ~8s and means the run is in the doomed per-candidate retry loop (R2a + R3).

### 3.3 Quota is dead — what still works

| Workflow | Works offline? |
|---|---|
| `--match-only` against البركة شركات (cache-first) | ⚠️ partially — see §4 known-good/known-bad |
| `seed_tawreed_to_cache.py` | ✅ fully (never calls Cohere) |
| `pre_translate_catalog.py --dry-run` | ✅ fully (plan only) |
| `pre_translate_catalog.py` (real Cohere) | ❌ pointless until quota resets |
| Tawreed API matching (no excel-target) | ✅ fully |

### 3.4 When quota resets (next month)

1. Run the dry-run plan first:

```powershell
python scripts\pre_translate_catalog.py --dry-run `
  --excel "data\input\excel target\البركة شركات.xlsx" --name-col "الصنف"
```

2. If the plan says N calls and N ≤ remaining quota → run it for real. If N > remaining → raise `--fuzzy-cutoff` work first (seed more from tawreed, translate fewer) or upgrade the key.

3. **Budget rule:** 1000 calls/month ÷ 50 names per batch call = **50,000 names/month ceiling**. The البركة catalog alone needs ~1-2 calls per run-month. Never run live translation per-candidate inside matching — batch only.

## 4. Known-good vs known-bad on the current data

**Known-good matches** (from run 20260904_1954_6, spot-checked):

| Item | Matched | Reason it's right |
|---|---|---|
| AGGREX 75 MG 60 TAB | اجركس 75 مجم 60 قرص س ق | brand transliteration + strength + pack |
| LEZBERG TRIO 20/5/12.5 30TAB | مارفينتس 20/5/12.5م 30 كبسوله | dosage triple + pack (verify brand manually!) |

**Known-bad** (wrong-brand, do not trust):

| Item | Matched | Why wrong |
|---|---|---|
| JACKODAN FACIAL WASH 150ML | اليجا غسول للوجه 150 مل | form/pack match only |
| ACTOS 30 MG 30TAB | سالبوفنت 30قرص | pack match only |
| BRAYTOFLEX 30 TAB | سالبوفنت 30قرص | pack match only |
| INODEP CAPSULES 30 | سالبوفنت 30قرص | pack match only |

**Rule of thumb for the analyst:** trust a match only when the **transliterated brand** of the Arabic name resembles the English brand (e.g. `اجركس`↔AGGREX). Matches justified only by "30قرص"/"150 مل" are noise.

## 5. Interpreting artifacts

```
artifacts\excel-target\البركة شركات\<run_ts>\match_only_summary_البركة شركات.csv
```

- **0-byte CSV** = run was killed/failed before writing rows. Ignore it; the newest *non-empty* CSV is the real latest result.
- **Score column** is currently unreliable (mixed scales, see R5). Treat `status` as authoritative: `matched-only` vs `no-results`, then manually verify brands per §4 rule of thumb.
- `final_reason` on `no-results` rows explains the rejection path.

Run DB (source of truth for statuses):

```powershell
python -c "
import sqlite3
c = sqlite3.connect(r'state\order_runs.db')
for r in c.execute('''select r.run_key, i.status, count(*) from run_items i
                      join runs r on i.run_key=r.run_key
                      where i.source_kind='excel-target'
                      group by r.run_key, i.status
                      order by r.started_at desc limit 12'''):
    print(r)
"
```

## 6. Escalation paths (pick one)

| Option | Cost | When |
|---|---|---|
| Wait for monthly reset | free | urgent-ness low, catalog mostly cached |
| Cohere Production key | pay-per-use | matching quality matters now |
| Increase tawreed seeding coverage (fuzzy-cutoff 75) | free | more cache hits before quota returns |
| Manual review discipline (`manual-review-only`) | human time | safest under current scores bug |

**Recommended while waiting for code fixes:** option 4 — run tiny, kill on 429 storm, verify brands by eye, log decisions in manual review so Run 2 improves.

## 7. Pre-flight checklist (copy into run ticket)

```
[ ] quota check: last run log has no "1000 API calls / month" 429?
[ ] cache check: translation_cache count > 4100?
[ ] limit small (--limit 3) for first run of the day?
[ ] watched first minute — no 429 storm?
[ ] CSV non-empty after run?
[ ] spot-checked 3 matches against §4 rule of thumb?
```
