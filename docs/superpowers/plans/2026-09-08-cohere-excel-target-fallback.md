# Excel Target Match — Cohere Fallback Implementation Plan

> **For agentic workers:** Use the executing-plans workflow with disjoint subagent write sets, TDD, security review, and a final two-axis code review.

**Goal:** Add Cohere as the final Excel-target translation fallback, using SQLite translation caching, batches of 50 names, and automatic failover between two local API keys.

**Architecture:** Local Tawreed and Egyptian dictionaries remain offline identity sources. Cached translations are read before any live call. At Excel index-build time only, unresolved unique Arabic names are sent to Cohere in batches of up to 50, persisted to `translation_cache`, and reused for all item matches.

**Tech Stack:** Python, Cohere `ClientV2`, SQLite, pytest/unittest.mock, python-dotenv.

**Spec:** User-provided implementation request in this conversation.

**BASE_SHA:** `e98cd8e6b5ba5925060628af58b8b6b3b90c4c1c`

## Global Constraints

- Source precedence: native English, Tawreed, Egyptian dictionary, SQLite cache, Cohere.
- Maximum batch size: 50 names per Cohere call.
- Maximum rate: 20 calls/minute per key.
- Rotate to the next key on quota, billing, invalid, or expired-key failures.
- Do not print, commit, or hardcode API keys.
- Tests must mock Cohere and never perform live requests.

## Parallel Workstreams

### Task 1: Cohere provider, batching, and cache correctness

**Files:**
- Modify: `src/core/normalization/translation.py`
- Modify: `tests/core/normalization/test_translation.py`
- Modify: `scripts/pre_translate_catalog.py`

Implement numbered-key loading, per-key clients/rate limiters, quota failover, a hard batch cap of 50, and normalized cache lookup. Remove per-item fallback calls from the batch path. Keep `ar_to_en_many` as the stable caller interface.

Use TDD: add one failing test for each seam, implement the smallest behavior, then run the focused test.

### Task 2: Excel source hierarchy and index-time live translation

**Files:**
- Modify: `src/core/excel_target/excel_target_identity.py`
- Modify: `tests/core/excel_target/test_excel_target.py`
- Modify: `tests/core/excel_target/test_baraka_safe_matching.py`

Build the identity index with Tawreed before Egyptian, cache before Cohere, and call live translation only once while constructing the index. Add the deterministic `allow_live_translation=False` test seam and preserve safe compatibility filtering.

### Task 3: Secret and configuration cleanup

**Files:**
- Modify: `.env.example`
- Modify: tracked diagnostic scripts containing direct Cohere key assignments
- Add: focused secret/configuration test if needed

Remove hardcoded key values, document `COHERE_API_KEY_1`, `COHERE_API_KEY_2`, `COHERE_BATCH_SIZE=50`, `COHERE_RATE_LIMIT_PER_MIN=20`, and `COHERE_TRANSLATION_MODEL=command-a-translate-08-2025`. Never read or modify the real `.env` from a subagent.

## Execution and Review Checkpoints

1. Record `BASE_SHA` and work in the existing non-main feature branch/worktree.
2. Spawn Tasks 1–3 concurrently with disjoint write sets; each agent uses TDD and pytest mocks.
3. Review each returned diff and test result before integration.
4. Run the focused and full test suites in the integration workspace.
5. Run OWASP secret checks and `git grep` for leaked Cohere assignments.
6. Run clean-code-guard on all production changes and fix findings.
7. Run code-review against `BASE_SHA` with separate Standards and Spec reviewers.
8. Re-run all tests after review fixes.

## Acceptance Tests

- 50 uncached names produce exactly one provider call; 51 produce two calls.
- Dictionary/cache hits produce zero Cohere calls.
- Cohere results persist in `translation_cache` and are reused on the next run.
- Terminal quota failure on key 1 switches the current batch to key 2.
- Per-minute throttling waits on the same key.
- Both keys exhausted leaves unresolved names unmatched rather than guessing.
- No secret remains in tracked source files or scripts.
