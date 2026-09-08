# Fix Plan — البركة شركات Matching Pipeline

Prerequisites: read `01-root-cause-analysis.md` first. Each fix references root causes (R1–R7) from that document.

**Ordering principle:** F1 and F2 stop the bleeding (thousands of doomed API calls). F3 verifies/repairs cache integrity. F4–F6 fix quality. F7 is polish. Do not reorder without understanding dependencies: F1's breaker makes F2's trace-call fix safer to validate, and F3's verification decides whether a backfill script is needed.

---

## F1 — Circuit breaker + failure semantics in the translation layer  (fixes R1, R3, R4)

**Files:** `src/core/normalization/translation.py`

### F1.1 — Add a module-level breaker

```python
class _ProviderBreaker:
    """Open on repeated consecutive provider failures; half-open after cooldown."""

    def __init__(self, threshold: int = 3, cooldown_s: float = 300.0):
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._consecutive = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at >= self.cooldown_s:
                self._opened_at = None          # half-open: one probe
                self._consecutive = self.threshold - 1
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._consecutive = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive += 1
            if self._consecutive >= self.threshold:
                self._opened_at = time.monotonic()

_breaker = _ProviderBreaker()
```

### F1.2 — Distinguish terminal quota from transient rate limit

`_call_cohere` must parse the 429 body:

```python
# inside the except block where status_code == 429:
body_text = str(getattr(exc, "body", "") or "")
if "/ month" in body_text or "1000 API calls" in body_text:
    logger.error("cohere monthly quota exhausted — disabling live translation for this process")
    _quota_dead.set()          # threading.Event
```

`_quota_dead` is checked **before** the rate limiter. When set, `_call_cohere` returns `None` immediately with zero HTTP traffic.

### F1.3 — Stop double-calling on failure

In `_lru_translate` (translation.py:248-256) and the batch path:

```python
primary = _call_cohere(PRIMARY_MODEL, cleaned)
if primary is None:
    # fallback only makes sense for transient single-name errors,
    # not for breaker-open or quota-dead states
    if _breaker.allow() and not _quota_dead.is_set():
        primary = _call_cohere(FALLBACK_MODEL, cleaned)
```

### F1.4 — Failure must be visible, not Arabic-as-English

Change the return contract: return `""` (not `cleaned`) when translation failed, and let callers skip empty strings. `excel_target_matching.py:166` already skips `not translated` — this aligns them.

```python
return primary or ""
```

⚠️ **Contract change:** grep all `ar_to_en` call sites before merging (expected: `bilingual_brand_matcher.py:234`, `excel_target_matching.py:164`, batch CLI). Update any that treat "returns input unchanged" as the failure signal.

**Acceptance criteria:**
- With network disabled: run completes offline, translations come from cache only, zero HTTP attempts after the first 3 failures.
- Unit test: mock 3 consecutive 429s → breaker opens → `_call_cohere` not called again for 5 minutes (inject monotonic clock).
- Unit test: quota-dead message → `_quota_dead` set → all subsequent calls short-circuit.

---

## F2 — Kill the live-Cohere "trace" calls  (fixes R2a)

**File:** `src/core/excel_target/excel_target_matching.py`

`match_brand(item_name, product.name)` at lines **147** and **175** executes all four tiers (including live Cohere) just to write a trace record. Replace with a read-only tracer:

1. In `bilingual_brand_matcher.py`, extract the read-only part:

```python
def match_brand_readonly(en_query: str, ar_row: str) -> BrandMatch:
    """Tawreed + dictionary tiers only. Never calls Cohere.
    Tier 3 consults the persistent cache WITHOUT a live fallback."""
```

2. Point both trace call sites at `match_brand_readonly`.

3. The real scoring in the top-30 loop (`:168`) already uses `_translation_score` + `_compatibility_factor` directly — leave that, but note it *also* calls `ar_to_en` (live path). After F1/F3, that call is cache-first; add `ar_to_en_cached_only()` (see F3) for the matching path so matching NEVER triggers live calls:

```python
# excel_target_matching.py:159
from src.core.normalization.translation import ar_to_en_cached_only
```

**Rationale:** interactive matching must be a pure local computation. Live translation belongs in the batch pre-translate CLI (`scripts/pre_translate_catalog.py`), not inside a per-candidate scoring loop.

**Acceptance criteria:**
- Run with network disabled → matching completes; cache-miss names simply don't score via the translation tier.
- Log line count: zero `httpx` POST lines to api.cohere.com during a full match-only run.

---

## F3 — Cache-integrity verification + `ar_to_en_cached_only`  (fixes R2b)

**Step 1 — verify (before writing any fix):**

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "
from src.core.database.translation_cache import TranslationCache, normalize_key
tc = TranslationCache()
for name in ['كونكور 5مجم 30قرص س ج', 'ايوكال كريم صغير 30جم', 'سالبوفنت 30قرص']:
    k = normalize_key(name)
    hits = tc.get_many([name])
    print(repr(name), '->', repr(k), '->', bool(hits))
"
```

- All hit → R2b is disproved; the misses in the run were legitimately-untranslated names (the 143 from the seeder session) — proceed with Step 2 only.
- Any miss → key-shape bug between seeder writer and runtime reader; diff `normalize_key` outputs against the `normalized_ar` column values written by the seeder and fix the divergent normalization step.

**Step 2 — add cached-only API:**

```python
# translation.py
def ar_to_en_cached_only(name: str) -> str:
    """Return cached translation or ''. Never contacts Cohere."""
    cleaned = _clean(name)
    if not cleaned:
        return ""
    cache = _persistent()
    if cache is None:
        return ""
    try:
        hits = cache.get_many([cleaned])
        return hits.get(normalize_key_for_lru(cleaned), "")
    except Exception:
        return ""
```

**Step 3 (conditional) — backfill script:** if verification shows legit misses used during matching, extend `scripts/pre_translate_catalog.py` with `--from-run-db` mode: read distinct `matched_name_ar` candidates from `order_runs.db` and batch-translate them *ahead* of the run (respecting the quota: max 1000/month → warn when the plan exceeds remaining quota).

**Acceptance criteria:**
- Verification transcript committed to `docs/postmortem/` (append evidence section).
- `ar_to_en_cached_only` covered by a unit test with a temp DB fixture.

---

## F4 — Fix the score scale  (fixes R5)

**Files:** `src/core/excel_target/excel_target_matching.py`, CSV writers, `run_items` persistence.

**Decision (need sign-off):** the canonical scale for `SearchMatch.score` in this codebase is what? Tawreed path emits 0..100 (`score * 100` at `:191` is consistent with that). The bilingual path computes 0..1 internally — that's fine — but the **CSV summary** shows values like `11.00` and `90.00` from *different* paths:

1. Audit `_finalize_fallback` (`:180`): `score * 100` — 0..1 → 0..100. ✓ consistent with Tawreed.
2. Audit the **dictionary direct-hit path** (`:117-127`): `dict_score` is already 0.9–0.97 in 0..1 scale, gets `* 100` → 90–97. But observed CSV scores are 5–15 for those rows → something else is writing them.
3. **Suspect:** the CSV `score` column is populated from a different field (e.g. `deterministic_score` or `decision.best_match.score` post-reconciliation) — trace the actual writer in `cli_order_excel_target.py` and pin the exact expression.

**Fix:** one scale (0..100) end-to-end. Assert in the summary writer:

```python
assert 0 <= float(score) <= 100.0001, f"score out of range: {score!r}"
```

(fail loud in debug, clamp+log in release).

**Acceptance criteria:** re-run 20260904_1954_6's input; every CSV score is in [0, 100]; the three `سالبوفنت` wrong matches now score < 70.

---

## F5 — Tighten acceptance to prevent wrong-drug matches  (fixes R6)

**Files:** `src/core/excel_target/excel_target_matching.py`, `src/core/normalization/bilingual_brand_matcher.py`

1. **Brand-similarity gate:** a candidate is acceptable only if its *brand* (not full name) similarity clears the bar:

```python
brand_score = fuzz.token_set_ratio(en_brand, translated_brand) / 100.0
if brand_score < 0.75:          # brand must match, not just form/pack
    continue
```

`ACTOS` vs `سالبوفنت`(Salbutamol) → transliterated brand `s l b f n t` vs `a k t s` → shared ≈ 0 → rejected.

2. **Require brand-tier evidence:** dictionary hit OR translation brand_score ≥ 0.75. Form/strength/pack compatibility may only *boost* (× factor), never *qualify* a candidate on its own. Today a pure pack match ("30قرص") + compat 1.0 can clear 0.7 with a garbage translation — that is exactly the `سالبوفنت` × 3 pathology.

3. **Raise `bilingual_min_score`** from 0.7 → 0.75 in `state/config.yaml` (`matching.bilingual_min_score`) *after* F4 makes scores trustworthy. Trade-off: more `no-results` (which route to manual review — correct behavior under `--flagged-match-action manual-review-only`).

4. **Cap compat factor influence:** compat is a multiplier in [0.6, 1.0]; it can never lift a candidate above min_score on its own — verify no path multiplies by >1.

**Acceptance criteria:**
- Unit tests: ACTOS→سالبوفنت rejected; AGGREX 75MG→اجركس 75مجم accepted; JACKODAN→اليجا rejected.
- Golden-file test on the 38-item sheet: expected ≥ 30 correct, ≤ 8 no-results, 0 wrong-brand matches.

---

## F6 — Atomic CSV writes  (fixes R7)

**File:** `src/cli/commands/cli_order_excel_target.py`

Write to `<name>.csv.tmp` then `os.replace()` at completion. On exception/kill: tmp is discarded; latest *complete* CSV remains newest-on-disk.

```python
tmp_path = target_summary.with_suffix(".csv.tmp")
with tmp_path.open("w", newline="", encoding="utf-8-sig") as fh:
    ...
os.replace(tmp_path, target_summary)
```

**Acceptance criteria:** kill -9 mid-run → no 0-byte summary; artifact dir holds only complete CSVs (+at most one .tmp). Add cleanup of stale `.tmp` files at run start.

---

## F7 — Telemetry: make quota visible  (supporting)

**File:** `src/core/normalization/translation.py`

- Log `x-trial-endpoint-call-remaining` (and month-quota variants) at WARNING when ≤ 50.
- Expose `translation_provider_status()` returning `{"quota_dead": bool, "breaker_open": bool, "consecutive_failures": int}` and print it in the command summary (`cli_shared.print_command_summary`).

**Acceptance criteria:** the run summary states explicitly whether live translation was available during the run.

---

## Implementation order & sizing

| Step | Fixes | Est. LOC | Risk | Depends on |
|---|---|---|---|---|
| 1 | F3.1 verification script only | 0 (evidence) | none | — |
| 2 | F1 breaker + quota-dead + return-"" | ~120 | medium (contract change) | — |
| 3 | F2 readonly tracer + cached-only matching | ~80 | low | F1 merged |
| 4 | F4 score-scale audit + fix | ~60 | medium (touches writers) | F2 (real scores visible) |
| 5 | F5 brand gate + threshold bump | ~50 | low | F4 |
| 6 | F6 atomic CSV | ~25 | none | — |
| 7 | F7 telemetry | ~40 | none | F1 |

Total: ~375 LOC + tests. Suggested split: one PR per step, each green on `pytest tests/ -k "translation or excel_target"` before merge.

## Verification protocol (after all fixes)

```powershell
# 1. Offline determinism (no network): run must complete, zero httpx lines
# 2. Golden run: 38-item sheet → expected counts from F5 acceptance
# 3. Quota-dead simulation: fake 429-month body → breaker opens, run completes offline
# 4. Kill-mid-run: no 0-byte CSVs
```
