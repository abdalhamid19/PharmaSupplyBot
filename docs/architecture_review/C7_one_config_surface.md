# C7 — One config surface

**Strength:** Strong (partial) — the credential/name-collision parts are Strong; the factory validation is Worth exploring.
**Tag:** local-substitutable

## Files

- `src/core/config/config.py` (55, `load_config` — reads `state/config.yaml`)
- `src/core/config/config_factory.py` (86)
- `src/core/config/config_models.py` (104, `MatchingConfig` v1: thresholds like `medium_score_threshold`)
- `src/core/drug_matching/config/config_models.py` (42, `MatchingConfig` v2: *different* fields — `fuzzy_threshold`, `brand_prefix_min`, …, plus `Paths` hardcoded to `artifacts/wardany/tawreed_products.csv`)
- `src/cli/cli_config.py` (382, `~/.pharmabotrc` + `./.pharmabotrc` + presets)
- `src/ui/streamlit_shared.py:20-21` (`DEFAULT_CONFIG_PATH` + example fallback)
- `src/ui/manual_review/streamlit_manual_review_cli.py:21,72` (hardcoded `state/config.yaml`)
- `src/cli/commands/item_worker.py:85` and `cli_order_execution.py:150` (hardcoded `"state/config.yaml"`)
- `src/tawreed/auth/tawreed_session_auth.py:22-23`, `tawreed_headless_auth_refresh.py:96-97`, `src/ui/auth/streamlit_headless_auth.py:68-73` (three independent readers of `TAWREED_EMAIL` / `TAWREED_PASSWORD`)

## Problem

At least five reading paths exist: YAML factory, `.pharmabotrc`, `.env`, streamlit secrets, and hardcoded defaults. Two different `MatchingConfig` classes share a name in different packages with disjoint fields; both are called "matching config" by callers (`bot.config.matching` is v1; `MatchPipeline(cfg)` takes v2). Worker subprocesses re-load YAML from a serialized *path string* (`item_worker.run_order_chunk` → `load_config(payload["config_path"])`) — config identity travels as a string across processes.

`os.getenv` / dotenv reading is scattered: `run.py:25`, `src/ui/streamlit_main.py:21`, `src/core/database/database_credentials.py:21-25` (each calls `load_dotenv()` itself). The `TAWREED_EMAIL`/`TAWREED_PASSWORD` env vars are read independently in three places. `SQLITE_DB_PATH` / `MANUAL_REVIEW_DB_PATH` env names live only inside `database_credentials.py`, referenced by string in UI help text (`streamlit_manual_review.py:46`).

The docs even record a past incident: `docs/METHYL_FOLATE_ORCHIDIA_MISMATCH_ANALYSIS.md` documents `reject_extra_brand_token` existing in YAML but unread by the model — i.e., YAML keys ↔ dataclass fields is enforced nowhere (config_factory has a hand-maintained string set at `config_factory.py:15-16`).

## Solution

One `src/core/config` public interface:

- `load_app_config(path) -> AppConfig` (already exists).
- `load_credentials() -> Credentials` — absorb dotenv / getenv / streamlit-secrets precedence.
- Make the factory derive allowed keys from `MatchingConfig.__dataclass_fields__` instead of a hand-written string set, so YAML keys are validated against the model.
- Rename `drug_matching`'s config to `OfflineMatchSettings` to end the name collision.

## Before / After

### Before — five sources, two `MatchingConfig` classes, no validation

```mermaid
flowchart LR
  Y[state/config.yaml] --> F1[config_factory.py<br/>string allowlist]
  P[.pharmabotrc] --> CLI[cli_config.py]
  E[.env] --> A1[tawreed_session_auth.py]
  E --> A2[tawreed_headless_auth_refresh.py]
  E --> A3[streamlit_headless_auth.py]
  S[streamlit secrets] --> A3
  H[hardcoded 'wardany' / 'state/config.yaml'] --> U1[streamlit_manual_review_cli.py]
  H --> U2[item_worker.py]
  F1 --> M1[MatchingConfig v1<br/>thresholds]
  F1 --> M2[MatchingConfig v2<br/>fuzzy_threshold …]
  M1 -. bot.config.matching .-> B[TawreedBot]
  M2 -. MatchPipeline(cfg) .-> P2[drug_matching.pipeline]
  classDef leak stroke:#dc2626,stroke-width:2px;
  class F1,A1,A2,A3,H leak
```

### After — one interface, two concrete readers, one validated model

```
  ┌───────────────────────────────┐
  │ src/core/config (interface)  │
  │ load_app_config(path)        │
  │ load_credentials()           │   ← small interface
  └──────────────┬────────────────┘
                 │ deep implementation
                 ▼
  ┌───────────────────────────────┐
  │ YAML → AppConfig (validated)  │
  │ .env / secrets → Credentials │
  │ derived from __dataclass_fields__
  │ name collision ended:         │
  │   MatchingConfig (online)     │
  │   OfflineMatchSettings (off)  │
  └───────────────────────────────┘
        ▲                ▲
        │                │
   CLI / Workers      UI / Auth
```

## Wins

- one place answers "where does X come from"
- name collision ends
- YAML keys validated by the model, not a string list
- credentials precedence (env over secrets over example) lives in one module
- prevents the next "key in YAML but unread by the model" incident
- locality: a YAML rename is a single-file edit caught at parse time
