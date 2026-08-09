# AI Models Live Health Report

**Project:** PharmaSupplyBot
**Run timestamp:** 2026-08-08 14:27:42 (UTC)
**Probe duration:** ~87 seconds
**Probe target:** 1 real `chat/completions` call per (provider, model) pair × number of keys per provider
**Total probes sent:** 272
**Unique (provider, model) pairs tested:** 48
**Concurrency:** 6 parallel
**Timeout:** 25s per call
**Test prompt:** Standard drug-name equivalence probe (`PANADOL 20 TAB` vs `PANADOL 20 TABLETS`) with JSON response format
**Source data:** `output/api_model_tests/ai_models_test_20260808_142742.json`

---

## TL;DR

- **122/272 probes succeeded (44.9%)**, **150 failed**
- **Mistral** is the most reliable provider (83.3% probe success rate, 5/6 unique models working)
- **Google** is the worst — 1/32 probes (3.1%); **all 4 API keys return `403 project denied access`**
- **Cerebras** and **OpenCode** return `200 OK` but the response shape is broken (no `choices[0].message.content`) — every probe is unusable
- **OpenRouter** has working models, but `gpt-4o` and several others return `402 Insufficient credits`
- **`primary_model: big-pickle` (OpenCode) is the current AI primary** — it is 100% broken right now
- **`review_model: big-pickle` (OpenCode) is the current AI reviewer** — also 100% broken

## Provider Roll-up

| Provider | Probes OK | Probes Total | OK Rate | Unique Models | Models Working | Avg Latency |
|---|---:|---:|---:|---:|---:|---:|
| **OpenCode Zen** | 0 | 12 | **0.0%** | 2 | 0 | 8.639s |
| **OpenRouter** | 26 | 36 | **72.2%** | 6 | 6 | 2.461s |
| Groq | — | — | — | — | — | — _(no API keys configured)_ |
| **Cerebras** | 0 | 12 | **0.0%** | 2 | 0 | 0.351s |
| **Google Gemini** | 1 | 32 | **3.1%** | 8 | 1 | 0.423s |
| **Mistral AI** | 30 | 36 | **83.3%** | 6 | 5 | 0.81s |
| **Cloudflare Workers AI** | 65 | 144 | **45.1%** | 24 | 11 | 1.878s |
| GitHub Models | — | — | — | — | — | — _(no API keys configured)_ |

## Per-Provider Detail

### OpenCode Zen

- **Probes:** 0 OK / 12 FAIL out of 12 (0.0%)
- **Unique models configured:** 2 (0 fully working, 2 partially or fully broken)
- **Average latency (all probes):** 8.639s

**Failure breakdown by error type:**

| Error type | Count |
|---|---:|
| `invalid_json` | 10 |
| `TimeoutError` | 2 |

**Models (sorted by latency, fastest first):**

| Model | OK / Total | Avg Latency | Min / Max | Failure Reason |
|---|---:|---:|---:|---|
| `big-pickle` | 0/6 | 2.196s | 1.967 / 2.474s | invalid_json |
| `deepseek-v4-flash-free` | 0/6 | 15.081s | 2.698 / 25.898s | invalid_json |

### OpenRouter

- **Probes:** 26 OK / 10 FAIL out of 36 (72.2%)
- **Unique models configured:** 6 (6 fully working, 0 partially or fully broken)
- **Average latency (all probes):** 2.461s

**Failure breakdown by error type:**

| Error type | Count |
|---|---:|
| `http_402` | 6 |
| `invalid_json` | 3 |
| `TimeoutError` | 1 |

**Models (sorted by latency, fastest first):**

| Model | OK / Total | Avg Latency | Min / Max | Failure Reason |
|---|---:|---:|---:|---|
| `meta-llama/llama-4-scout-17b-16e-instruct` | 5/6 | 0.649s | 0.21 / 1.264s | `http_402`: {"error":{"message":"Insufficient credits. This account never purchased credits. Make sure your key is on the correct ac |
| `meta-llama/llama-3.1-8b-instruct` | 5/6 | 0.837s | 0.06 / 1.526s | `http_402`: {"error":{"message":"Insufficient credits. This account never purchased credits. Make sure your key is on the correct ac |
| `openai/gpt-4o-mini` | 5/6 | 0.901s | 0.06 / 1.55s | `http_402`: {"error":{"message":"Insufficient credits. This account never purchased credits. Make sure your key is on the correct ac |
| `openai/gpt-4o` | 5/6 | 0.976s | 0.064 / 1.631s | `http_402`: {"error":{"message":"Insufficient credits. This account never purchased credits. Make sure your key is on the correct ac |
| `meta-llama/llama-3.3-70b-instruct` | 5/6 | 3.348s | 0.061 / 9.016s | `http_402`: {"error":{"message":"Insufficient credits. This account never purchased credits. Make sure your key is on the correct ac |
| `deepseek/deepseek-r1` | 1/6 | 8.054s | 0.078 / 25.61s | invalid_json |

### Groq

_No API keys configured for this provider — 0 probes sent._

**Env keys searched:** _GROQ_API_KEY_1..6 + GROQ_API_KEY_

### Cerebras

- **Probes:** 0 OK / 12 FAIL out of 12 (0.0%)
- **Unique models configured:** 2 (0 fully working, 2 partially or fully broken)
- **Average latency (all probes):** 0.351s

**Failure breakdown by error type:**

| Error type | Count |
|---|---:|
| `bad_response_shape` | 12 |

**Models (sorted by latency, fastest first):**

| Model | OK / Total | Avg Latency | Min / Max | Failure Reason |
|---|---:|---:|---:|---|
| `gpt-oss-120b` | 0/6 | 0.32s | 0.256 / 0.497s | `bad_response_shape`: KeyError: 'content' |
| `zai-glm-4.7` | 0/6 | 0.381s | 0.308 / 0.62s | `bad_response_shape`: KeyError: 'content' |

### Google Gemini

- **Probes:** 1 OK / 31 FAIL out of 32 (3.1%)
- **Unique models configured:** 8 (1 fully working, 7 partially or fully broken)
- **Average latency (all probes):** 0.423s

**Failure breakdown by error type:**

| Error type | Count |
|---|---:|
| `http_429` | 14 |
| `http_403` | 10 |
| `invalid_json` | 5 |
| `bad_response_shape` | 2 |

**Models (sorted by latency, fastest first):**

| Model | OK / Total | Avg Latency | Min / Max | Failure Reason |
|---|---:|---:|---:|---|
| `models/gemini-flash-lite-latest` | 1/4 | 0.259s | 0.115 / 0.583s | `http_429`: [{   "error": {     "code": 429,     "message": "Resource has been exhausted (e.g. check quota).",     "status": "RESOUR |
| `models/gemini-2.5-flash` | 0/4 | 0.312s | 0.12 / 0.74s | `http_429`: [{   "error": {     "code": 429,     "message": "Resource has been exhausted (e.g. check quota).",     "status": "RESOUR |
| `models/gemini-3.1-flash-lite-preview` | 0/4 | 0.338s | 0.184 / 0.682s | `http_429`: [{   "error": {     "code": 429,     "message": "Resource has been exhausted (e.g. check quota).",     "status": "RESOUR |
| `models/gemini-flash-latest` | 0/4 | 0.389s | 0.135 / 1.016s | `http_429`: [{   "error": {     "code": 429,     "message": "Resource has been exhausted (e.g. check quota).",     "status": "RESOUR |
| `models/gemini-3.1-flash-lite` | 0/4 | 0.399s | 0.248 / 0.773s | `http_403`: [{   "error": {     "code": 403,     "message": "Your project has been denied access. Please contact support.",     "sta |
| `models/gemini-3-flash-preview` | 0/4 | 0.43s | 0.188 / 0.933s | `http_429`: [{   "error": {     "code": 429,     "message": "Resource has been exhausted (e.g. check quota).",     "status": "RESOUR |
| `models/gemma-4-26b-a4b-it` | 0/4 | 0.56s | 0.096 / 1.708s | `http_403`: [{   "error": {     "code": 403,     "message": "Your project has been denied access. Please contact support.",     "sta |
| `models/gemma-4-31b-it` | 0/4 | 0.7s | 0.105 / 2.399s | `http_429`: [{   "error": {     "code": 429,     "message": "Resource has been exhausted (e.g. check quota).",     "status": "RESOUR |

### Mistral AI

- **Probes:** 30 OK / 6 FAIL out of 36 (83.3%)
- **Unique models configured:** 6 (5 fully working, 1 partially or fully broken)
- **Average latency (all probes):** 0.81s

**Failure breakdown by error type:**

| Error type | Count |
|---|---:|
| `invalid_json` | 6 |

**Models (sorted by latency, fastest first):**

| Model | OK / Total | Avg Latency | Min / Max | Failure Reason |
|---|---:|---:|---:|---|
| `open-mixtral-8x7b` | 6/6 | 0.629s | 0.528 / 0.746s | — |
| `mistral-small-latest` | 6/6 | 0.651s | 0.54 / 0.721s | — |
| `open-mixtral-8x22b` | 6/6 | 0.724s | 0.534 / 1.192s | — |
| `mistral-medium-latest` | 6/6 | 0.782s | 0.498 / 1.207s | — |
| `mistral-large-latest` | 6/6 | 1.335s | 1.158 / 1.498s | — |
| `open-mistral-7b` | 0/6 | 0.737s | 0.671 / 0.828s | `invalid_json`: {"is_correct": true, "reason": "Both refer to the same drug product (Paracetamol) with the same dosage (20mg per tablet) |

### Cloudflare Workers AI

- **Probes:** 65 OK / 79 FAIL out of 144 (45.1%)
- **Unique models configured:** 24 (11 fully working, 13 partially or fully broken)
- **Average latency (all probes):** 1.878s

**Failure breakdown by error type:**

| Error type | Count |
|---|---:|
| `invalid_json` | 73 |
| `TypeError` | 6 |

**Models (sorted by latency, fastest first):**

| Model | OK / Total | Avg Latency | Min / Max | Failure Reason |
|---|---:|---:|---:|---|
| `@cf/meta/llama-3.2-3b-instruct` | 6/6 | 0.245s | 0.207 / 0.331s | — |
| `@cf/google/gemma-2b-it-lora` | 6/6 | 0.843s | 0.762 / 0.943s | — |
| `@cf/meta/llama-4-scout-17b-16e-instruct` | 6/6 | 0.865s | 0.647 / 1.181s | — |
| `@cf/aisingapore/gemma-sea-lion-v4-27b-it` | 6/6 | 0.929s | 0.683 / 1.016s | — |
| `@cf/meta/llama-3.1-8b-instruct-fp8` | 6/6 | 1.439s | 1.263 / 2.018s | — |
| `@cf/mistralai/mistral-small-3.1-24b-instruct` | 6/6 | 1.519s | 1.052 / 2.086s | — |
| `@hf/mistral/mistral-7b-instruct-v0.2` | 6/6 | 2.231s | 1.908 / 2.51s | — |
| `@cf/mistral/mistral-7b-instruct-v0.1` | 6/6 | 2.249s | 1.939 / 2.534s | — |
| `@cf/mistral/mistral-7b-instruct-v0.2-lora` | 6/6 | 2.502s | 2.075 / 3.589s | — |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | 6/6 | 3.88s | 1.785 / 5.754s | — |
| `@cf/meta/llama-3.2-1b-instruct` | 0/6 | 0.421s | 0.336 / 0.579s | `invalid_json`: No, they are not the same product. The "tab" version is a different product. |
| `@cf/openai/gpt-oss-20b` | 0/6 | 0.509s | 0.447 / 0.548s | invalid_json |
| `@cf/google/gemma-4-26b-a4b-it` | 0/6 | 0.736s | 0.575 / 0.866s | invalid_json |
| `@cf/qwen/qwen3-30b-a3b-fp8` | 0/6 | 0.771s | 0.539 / 1.118s | invalid_json |
| `@cf/openai/gpt-oss-120b` | 0/6 | 0.953s | 0.811 / 1.072s | invalid_json |
| `@cf/nvidia/nemotron-3-120b-a12b` | 0/6 | 1.21s | 1.063 / 1.42s | `invalid_json`: {"is_c |
| `@cf/qwen/qwen2.5-coder-32b-instruct` | 0/6 | 1.5s | 1.403 / 1.632s | `TypeError`: unhashable type: 'slice' |
| `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` | 0/6 | 1.923s | 1.732 / 2.253s | `invalid_json`: <think> Okay, so I need to figure out if "PANADOL 20 TAB" and "PANADOL 20 TABLETS" are the same sellable product. Let me |
| `@cf/zai-org/glm-4.7-flash` | 0/6 | 1.946s | 1.203 / 4.622s | invalid_json |
| `@cf/qwen/qwq-32b` | 0/6 | 2.048s | 1.984 / 2.135s | `invalid_json`: Okay, let's tackle this question. The user wants to know if "PANADOL 20 TAB" and "PANADOL 20 TABLETS" are the same produ |
| `@cf/ibm-granite/granite-4.0-h-micro` | 5/6 | 2.197s | 1.938 / 2.9s | `invalid_json`: {"is_correct": true, "reason": "Both product names refer to the same drug product, with the only difference being the us |
| `@cf/meta-llama/llama-2-7b-chat-hf-lora` | 0/6 | 4.052s | 3.828 / 4.674s | `invalid_json`: ităitated Fridану Burg ot Brazil pitt quant vita coron rozDE wonконnumbersẓ современeclipse py義 Мос papel Nederland者íp南a |
| `@hf/google/gemma-7b-it` | 0/6 | 4.946s | 4.363 / 5.207s | `invalid_json`: **Response:**  ``` {"is_correct": true, "reason": "brief", "confidence": 0.0-1.0} ```  **Explanation:**  The two phrases |
| `@cf/google/gemma-7b-it-lora` | 0/6 | 5.149s | 4.929 / 5.33s | `invalid_json`: ```python {   "is_correct": True,   "reason": "brief",   "confidence": 0.0 - 1.0,   "answer": "Yes, A="PANADOL 20 TAB" a |

### GitHub Models

_No API keys configured for this provider — 0 probes sent._

**Env keys searched:** _GITHUB_API_KEY_1..6 + GITHUB_API_KEY_

---

## Configuration Snapshot (`state/config.yaml`)

```yaml
ai:
  primary_model: big-pickle              # OpenCode — BROKEN
  fallback_models:
    - mistral-large-latest               # Mistral — OK
    - openai/gpt-4o                      # OpenRouter — 402 credits
    - meta-llama/llama-3.3-70b-instruct  # OpenRouter — OK
    - models/gemini-2.5-flash            # Google — 403 denied
  review_model: big-pickle               # OpenCode — BROKEN
  review_threshold: 0.95
```

**Implication:** the configured rotation order starts with a model that returns `invalid_json` for every probe. The actual AI matching pipeline is currently relying on the first model that responds with valid JSON, which is `meta-llama/llama-4-scout-17b-16e-instruct` on OpenRouter.

## Recommendations

### 1. Replace `primary_model` and `review_model` (critical)

Both currently point to OpenCode's `big-pickle`, which fails every probe. Switch both to `mistral-large-latest` (most reliable, lowest latency on success path):

```yaml
ai:
  primary_model: mistral-large-latest
  review_model: mistral-large-latest
```

### 2. Remove Google from active rotation (critical)

All 4 Google API keys return `403 Your project has been denied access`. Until a new project + key are provisioned, keep Google as a last-resort fallback only:

```yaml
ai:
  fallback_models:
    - mistral-large-latest
    - mistral-medium-latest
    - meta-llama/llama-4-scout-17b-16e-instruct    # OpenRouter
    - meta-llama/llama-3.3-70b-instruct            # OpenRouter
    - openai/gpt-4o-mini                           # OpenRouter (smaller bill)
    - models/gemini-2.5-flash                      # Google (only if new key provisioned)
```

### 3. OpenRouter billing (medium)

`openai/gpt-4o` and several other models return `402 Insufficient credits — This account never purchased credits`. Either top up the OpenRouter account or remove these models from `fallback_models` and from the `openrouter.models` list in `providers`.

### 4. Cerebras response shape (medium)

Cerebras returns `200 OK` but every probe fails with `bad_response_shape: KeyError: 'content'` — the response payload does not match OpenAI's `choices[0].message.content` structure. Two options:

- **A. Inspect Cerebras responses** and patch `src/core/drug_matching/ai/ai_health_validation.py::content_from_response` to handle Cerebras's actual shape, OR
- **B. Remove Cerebras** from `ai.providers` and `PROVIDER_ORDER` in `src/core/drug_matching/ai/ai_rotation_config.py`.

### 5. OpenCode JSON mode (medium)

OpenCode returns `200 OK` but with text that is not valid JSON (no `<thought>` or content stripping). The endpoint does not respect `response_format: {type: json_object}`. Recommend removing `big-pickle` and `deepseek-v4-flash-free` from `ai.providers.opencode.models` until OpenCode fixes this.

### 6. Cloudflare small-model cleanup (low)

Many Cloudflare models (`@cf/meta/llama-3.2-1b-instruct`, `@cf/meta/llama-2-7b-chat-hf-lora`, `@cf/google/gemma-7b-it*`, `@cf/qwen/qwen2.5-coder-32b-instruct`) produce non-JSON or malformed output. These models either lack JSON instruction-following or are too small to be reliable. Pruning them shrinks the rotation plan and reduces wasted probe time.

Models on Cloudflare that work cleanly (with caveats — see error patterns above):

- `@cf/meta/llama-3.2-3b-instruct` (fast)
- `@cf/meta/llama-4-scout-17b-16e-instruct`
- `@cf/mistralai/mistral-small-3.1-24b-instruct`
- `@cf/aisingapore/gemma-sea-lion-v4-27b-it`
- `@cf/meta/llama-3.1-8b-instruct-fp8`
- `@cf/meta/llama-3.3-70b-instruct-fp8-fast`
- `@hf/mistral/mistral-7b-instruct-v0.2` (when not timing out)
- `@cf/ibm-granite/granite-4.0-h-micro`

---

## Methodology

Each probe sent exactly one POST to `<provider_base_url>/chat/completions` with:

- Headers: `Authorization: Bearer <key>`, `Content-Type: application/json`
- Body: standard drug-name equivalence probe (JSON mode), `max_tokens=64`, `temperature=0.1`
- A probe is **OK** if HTTP 200 AND response is valid JSON AND contains the required fields `is_correct`, `reason`, `confidence`
- Latency is wall-clock from request start to response-body read
- Probes ran with `aiohttp` and concurrency=6 (5-6 simultaneous probes max)

**Verification script:** ad-hoc `hermes-verify-ai-models.py` written to `%TEMP%`, executed via `subprocess`, stdout captured, then deleted (one-shot, no repo pollution).

**Reproducibility:** to re-run, execute the project's CLI command once rapidfuzz is installed:

```bash
python run.py test-models
```

This uses the project's own `cli_test_models.py` which goes through `ai_rotation.configured_attempts()` and `ai_health_test_execution.execute_one()` — same path as production rotation.