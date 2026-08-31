# 🗺️ سجل تطور المشروع — PharmaSupplyBot

> هذا ملف hand-off يوثّق رحلة الشغل على المشروع من البداية للوضع الحالي.
> آخر تحديث: 2026-07-31 (logging_system branch).

---

## المقدمة

**PharmaSupplyBot** هو CLI automation tool للصيدليات المصرية على موقع توريد (Tawreed.io).

بدأ المشروع كـ simple Playwright script وتطور عبر **مرحلتين رئيسيتين**، كل مرحلة فيها stages متعددة:

1. **المرحلة الأولى**: بناء الـ core product (matching + order + UI)
2. **المرحلة الثانية**: تحسين الـ infrastructure (CLI + logging + config)

---

## الجدول الزمني

```
2026-04-25 │ Initial commit
           │ بدأ المشروع: Playwright script بسيط لتسجيل الدخول على Tawreed
           ▼

═══════════════════════════════════════════════════════════
  المرحلة الأولى: بناء Core Product
  (April 25 → July 21, 2026 | ~140 commits على main)
═══════════════════════════════════════════════════════════

2026-04-25 │ 🟢 Initial setup
           │   • Playwright login + session management
           │   • Basic cart operations
           ▼
2026-05-xx │ 🟢 Product matching foundation
           │   • Normalized drug name matching
           │   • Fuzzy scoring + component matching
           │   • CLI command structure (argparse)
           │   • Streamlit UI (order form + results)
           ▼
2026-06-xx │ 🟢 AI integration
           │   • AI verification for low-confidence matches
           │   • Multi-provider rotation (groq, openrouter, google...)
           │   • Manual review system (SQLite)
           │   • Warehouse discount optimization
           ▼
2026-07-01 → │ 🟢 API integration + scaling
2026-07-20  │   • Tawreed API direct access (bypass browser)
             │   • Parallel item workers
             │   • Match-only mode (verification without ordering)
             │   • Export products CLI
             │   • Product matching CLI
             │   • Prevented items system
             │   • Extensive bug fixes (brand mismatch, numeric safety...)
             │   • 387 commits on main
             ▼

═══════════════════════════════════════════════════════════
  المرحلة الثانية: Infrastructure Improvements
  (July 21 → July 31, 2026 | 3 branches, ~50 commits)
═══════════════════════════════════════════════════════════

2026-07-21 │ 🔵 logging_system branch
           │   • Unified logging framework (stdlib `logging`)
           │   • Exception hierarchy + command registry
           │   • Structured JSON output
           │   • CI guard tests for logging audit
           │   • ~40 commits (not yet merged to main)
           ▼
2026-07-23 → │ 🟡 feature/cli-development (→ logging_system)
2026-07-29  │   • Migrated CLI from argparse to Typer + Rich
             │   • Shell tab-completion
             │   • User config (~/.pharmabotrc) + presets
             │   • CLI shortcut aliases (-x, -n, -p, -c)
             │   • Structured command-summary block
             │   • `--format` flag (human/json/plain)
             │   • `--json-log-records` + `--rich-logs`
             │   • Deleted deprecated argparse parser modules
             │   • E2E verification: 688 passing, 3 pre-existing failures
             ▼
2026-07-25 → │ 🟢 Stage 1+2: AI config migration to YAML
2026-07-31  │   • Stage 1: AI defaults (model/fallback/review/threshold)
             │     from .env → config.yaml ai: block
             │   • Stage 2: *_MODELS rotation pools from Python → YAML
             │     (ai_rotation_config.py shrunk from 210 → 16 lines)
             │   • Stage 3: PROVIDERS dict → YAML ai.providers.*
             │     (new ProviderMetadata + ProviderPool dataclasses)
             │   • Full test coverage: 736 passing + 6 pre-existing
             │   • README section for ai: config block
             ▼
2026-07-31 │ ✅ الوضع الحالي
           │   • logging_system branch active (not merged yet)
           │   • ai: block fully declarative in config.yaml
           │   • Backward-compat PROVIDERS alias preserved
```

---

## الفروع (Branches)

| Branch | الحالة | Commits | الوصف |
|---|---|---|---|
| `main` | ✅ stable | 387 | الكود الأساسي — product + matching + order |
| `logging_system` | 🔄 active (current) | 40 on top of main | CLI migration + logging + YAML config |
| `feature/cli-development` | → merged into logging_system | 0 unique | CLI development work (squashed into logging_system) |

---

## الـ Commits الرئيسية

### Phase 1: Core Product (`main` branch)

```
e8488d9  2026-04-25  Initial commit
f3205c4  2026-04-xx  Clean docstrings and line lengths
fe46e30  2026-04-xx  Extract configuration models
72052f3  2026-04-xx  Split config builders from loader
fd09e54  2026-05-xx  Extract product matching models and rules
9c62db8  2026-05-xx  Centralize Tawreed constants and selectors
bd6bb7d  2026-05-xx  Extract CLI parser and command runners
9dfa305  2026-05-xx  Add rule audit and document refactoring exceptions
f00d9c4  2026-05-xx  Add Streamlit GUI for Tawreed workflows
e7dd9dc  2026-06-xx  Add Tawreed match-only order mode
387999d  2026-06-xx  phase 1: add matching integration dependencies
2624eae  2026-06-26  phase 4: add tawreed api contract support
dc40707  2026-06-xx  phase 9: apply manual review decisions at runtime
042f621  2026-07-10  phase 02: fix component/brand matching (15+ false negatives)
5c3c2da  2026-07-10  phase 01: canonical dosage model and numeric safety fix
9116427  2026-07-14  phase 1: add validation harness
18e7aeb  2026-07-15  phase 12: add AI provider cooldown
5e61c5b  2026-07-21  Merge branch 'feature/cli-development'  ← main HEAD
```

### Phase 2: Infrastructure (`logging_system` branch)

```
3821166  2026-07-23  test(cli): E2E verification of Typer+Rich migration
cc67894  2026-07-23  docs: README sections for Typer/Rich migration
c7bb4d1  2026-07-23  fix(cli): validate --log-level via callback
884a7a4  2026-07-23  feat(cli): Rich progress spinner + RichHandler
3bd1e31  2026-07-23  refactor(cli): delete deprecated argparse parsers
68c1205  2026-07-23  test(cli): replace argparse tests with Typer CliRunner
9fb9441  2026-07-23  refactor(run): switch entry point to Typer app
b8b6be6  2026-07-23  feat(cli): wire order/match/remove-cart subcommands
af9e152  2026-07-23  feat(cli): scaffold Typer app + show-completion
4446811  2026-07-23  feat(cli): add ns_from_ctx Typer→argparse shim
9a045b6  2026-07-23  feat(cli): add FormatFlags + render_table presenter
51eb5d2  2026-07-23  deps: add typer>=0.12.0 and rich>=13.7.0
48bd7f2  2026-07-25  refactor(config): move AI defaults from .env → YAML (Stage 1)
2852fd0  2026-07-25  refactor(config): migrate *_MODELS to YAML (Stage 2)
e391fa8  2026-07-29  refactor(config): migrate PROVIDERS dict to YAML (Stage 3)
8c1fb58  2026-07-29  docs: README section for ai: config block
```

---

## الـ Architecture (الوضع الحالي)

```
PharmaSupplyBot/
├── run.py                          ← Typer entry point (CLI)
├── streamlit_app.py                ← Streamlit GUI entry point
├── config.yaml                     ← Active config (state/config.yaml for runtime)
├── config.example.yaml             ← Template with all options documented
├── state/
│   ├── config.yaml                 ← Runtime config (gitignored, loaded by Typer)
│   ├── wardany.json                ← Playwright session state
│   └── manual_review_decisions.db  ← SQLite store for manual review
├── .env                            ← API keys + per-run overrides (gitignored)
├── .env.example                    ← Template for .env
│
├── src/
│   ├── core/
│   │   ├── config/
│   │   │   ├── config_models.py    ← AIConfig + ProviderPool + ProviderMetadata
│   │   │   ├── config_helpers.py   ← resolve_api_config + _fallback_models
│   │   │   └── config_providers.py ← backward-compat PROVIDERS alias
│   │   ├── drug_matching/
│   │   │   ├── ai/
│   │   │   │   ├── ai_rotation.py  ← configured_attempts (reads YAML)
│   │   │   │   └── ai_rotation_config.py  ← PROVIDER_ORDER only (16 lines)
│   │   │   └── verification/verifier.py
│   │   └── ordering/
│   ├── cli/
│   │   ├── typer_app.py            ← Typer commands + _apply_ai_defaults
│   │   └── commands/               ← Registered command handlers
│   ├── tawreed/                    ← Playwright + API automation
│   └── ui/                         ← Streamlit views
│
├── tests/                          ← 736 passing, 6 pre-existing failures
│   └── core/drug_matching/
│       ├── test_ai_config.py       ← 18 tests (Stage 1)
│       ├── test_provider_pools.py  ← 18 tests (Stage 2)
│       └── test_provider_metadata.py  ← 18 tests (Stage 3)
│
└── docs/                           ← This file + other documentation
```

---

## الـ Precedence Chain (AI Config)

```
┌──────────────────────────────────────────────────────┐
│  CLI flag (highest)                                 │
│  --model openai/gpt-5 --review-model gemini-2.5-pro │
├──────────────────────────────────────────────────────┤
│  Environment variable                               │
│  AI_MODEL=... / REVIEW_MODEL=... / AI_MODEL=...     │
├──────────────────────────────────────────────────────┤
│  config.yaml (ai: block)                            │
│  ai.primary_model / ai.review_model / ai.providers.* │
├──────────────────────────────────────────────────────┤
│  Hardcoded defaults (lowest)                        │
│  AIConfig dataclass in config_models.py             │
└──────────────────────────────────────────────────────┘
```

---

## الإحصائيات النهائية

| Metric | القيمة |
|---|---|
| **Total commits** | 434 (across all branches) |
| **Main branch** | 387 commits (April 25 → July 21) |
| **logging_system branch** | 40 commits on top of main |
| **pytest passing** | 736 tests |
| **pre-existing failures** | 6 (unchanged across stages) |
| **New tests added (Stage 1-3)** | 54 unit tests |
| **Files changed (config migration)** | 21 files |
| **ai_rotation_config.py** | 210 → 16 lines |
| **config_providers.py** | 83 → 78 lines (shim) |
| **README.md** | 472 → 594 lines (+122 AI docs) |

---

## ماذا بعد؟ (Future Work)

- [ ] **Merge logging_system → main** (يحتاج CI + final verification)
- [ ] **Stage 4**: Clean up `config_factory.py` `_matching_*_keys` whitelists
  (يتحولوا لـ introspection على dataclass fields بدل magic strings)
- [ ] **Stage 5**: Fix cloudflare pair logic (pre-existing `zip` bug في
  `ai_rotation._provider_keys` — `CLOUDFLARE_API_TOKEN` single-key
  لازم يـ pair مع `CLOUDFLARE_ACCOUNT_ID` مش مع `ACCOUNT_ID_2`)
- [ ] **Stage 6**: Remove `PROVIDERS` dict alias (بعد ما الـ tests تتكتب
  تستعمل `get_provider_metadata` بدل `PROVIDERS[x]["base_url"]`)

---

## ملاحظات تقنية مهمة

### الـ Hermes Agent subprocess trap

```
PYTHONPATH=hermes-agent/venv/Lib/site-packages ميرث في كل subprocess
→ لازم env.pop("PYTHONPATH", None) + set USERPROFILE/HOME = tempfile
  في أي subprocess.run يشتغل على المشروع
```

### الـ Pre-existing failures (مش بتاعتنا)

```
1. test_async_matching_logging_uses_queue_handler_and_stops_listener
2. test_no_print_calls_in_src
3. test_process_single_item_cleans_up_on_success_skip_and_failure
4-6. test_cli_commands.py (3 tests — ValidationError edge cases)
```

### الـ config.yaml ≠ state/config.yaml

```
config.yaml          ← في git root (template/reference، مـcommit)
state/config.yaml    ← في state/ (runtime active، gitignored)
                       الـ CLI والـ Streamlit بيقرأوا state/config.yaml
```
