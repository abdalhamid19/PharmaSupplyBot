# الفحص الحي لنماذج الذكاء الاصطناعي (Live Check)

## النتيجة المختصرة

| القياس | القيمة |
|---|---|
| النماذج المفحوصة | **145** |
| استجاب 200 (HTTP) | **49** |
| JSON صالح (ok) | **29** |
| فشل | **116** |

### لكل مزوّد

| مزوّد | فحص | 200 | ok |
|---|---|---|---|
| `cerebras` | 5 | 2 | 0 |
| `cloudflare` | 53 | 24 | 13 |
| `github` | 41 | 0 | 0 |
| `google` | 18 | 9 | 4 |
| `groq` | 9 | 0 | 0 |
| `mistral` | 6 | 6 | 6 |
| `opencode` | 7 | 2 | 1 |
| `openrouter` | 6 | 6 | 5 |

## تفاصيل الفشل

| مزوّد | النموذج | حالة | نوع الخطأ | رسالة |
|---|---|---|---|---|
| `groq` | `openai/gpt-oss-120b` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `github` | `meta/meta-llama-3.1-405b-instruct` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cerebras` | `qwen-3-235b-a22b-instruct-2507` | 404 | http_404 | {"message":"Model does not exist or you do not have access to it.","type":"not_found_error","param":"model","code":"mode |
| `google` | `models/gemini-2.5-pro` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `cloudflare` | `@cf/openai/gpt-oss-120b` | 200 | invalid_json |  |
| `groq` | `meta-llama/llama-4-scout-17b-16e-instruct` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `opencode` | `nemotron-3-super-free` | 401 | http_401 | {"type":"error","error":{"type":"ModelError","message":"Model nemotron-3-super-free is not supported"}} |
| `openrouter` | `deepseek/deepseek-r1` | 200 | invalid_json |  |
| `github` | `deepseek/deepseek-r1-0528` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cerebras` | `gpt-oss-120b` | 200 | invalid_json |  |
| `google` | `models/gemini-3.1-pro-preview` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `cloudflare` | `@cf/nvidia/nemotron-3-120b-a12b` | 200 | invalid_json |  |
| `groq` | `qwen/qwen3-32b` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `opencode` | `minimax-m2.5-free` | 401 | http_401 | {"type":"error","error":{"type":"ModelError","message":"Model minimax-m2.5-free is not supported"}} |
| `github` | `deepseek/deepseek-r1` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `google` | `models/gemini-3.1-pro-preview-customtools` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `cloudflare` | `@cf/moonshotai/kimi-k2.6` | 403 | http_403 | {"errors":[{"message":"AiError: Model @cf/moonshotai/kimi-k2.6 is not available on the Workers Free plan: Model @cf/moon |
| `github` | `deepseek/deepseek-v3-0324` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `google` | `models/gemini-3-pro-preview` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `cloudflare` | `@cf/moonshotai/kimi-k2.5` | 403 | http_403 | {"errors":[{"message":"AiError: Model @cf/moonshotai/kimi-k2.6 is not available on the Workers Free plan: Model @cf/moon |
| `github` | `xai/grok-3` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `google` | `models/gemini-2.5-flash` | 200 | invalid_json | Here |
| `github` | `meta/llama-4-scout-17b-16e-instruct` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `openai/gpt-5` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/qwen/qwen3-30b-a3b-fp8` | 200 | invalid_json |  |
| `github` | `openai/o3` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/qwen/qwq-32b` | 200 | invalid_json | Okay, let's see. The user is asking if "PANADOL 20 TAB" and "PANADOL 20 TABLETS" are the same product. Hmm, first, I nee |
| `github` | `openai/o1` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/google/gemma-4-26b-a4b-it` | 200 | invalid_json |  |
| `github` | `openai/o1-preview` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `meta/llama-3.3-70b-instruct` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/qwen/qwen2.5-coder-32b-instruct` | 200 | invalid_json | {'is_correct': True, 'reason': "The product names differ only in the spelling of 'TAB' and 'TABLETS', which refer to the |
| `github` | `ai21-labs/ai21-jamba-1.5-large` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` | 200 | invalid_json | <think> Okay, so I need to figure out if "PANADOL 20 TAB" and "PANADOL 20 TABLETS" are the same sellable product. Let me |
| `github` | `cohere/cohere-command-a` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `openai/gpt-4.1` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/google/gemma-3-12b-it` | 403 | http_403 | {"errors":[{"message":"AiError: Ai: Account 105779725 is not allowed to access @cf/google/gemma-3-12b-it. (67d88c0f-f2b5 |
| `cloudflare` | `@cf/openai/gpt-oss-20b` | 200 | invalid_json |  |
| `cloudflare` | `@cf/meta/llama-3.1-8b-instruct-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/meta/llama-3.1-8b-instruct-awq was deprecated on 2026-05- |
| `cerebras` | `zai-glm-4.7` | 200 | invalid_json |  |
| `groq` | `llama-3.3-70b-versatile` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `opencode` | `deepseek-v4-flash-free` | 200 | invalid_json |  |
| `cerebras` | `llama-4-scout-17b-16e-instruct` | 404 | http_404 | {"message":"Model does not exist or you do not have access to it.","type":"not_found_error","param":"model","code":"mode |
| `groq` | `groq/compound` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `opencode` | `ring-2.6-1t-free` | 401 | http_401 | {"type":"error","error":{"type":"ModelError","message":"Model ring-2.6-1t-free is not supported"}} |
| `groq` | `openai/gpt-oss-20b` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `google` | `models/gemini-3-flash-preview` | 200 | invalid_json |  |
| `google` | `models/gemini-2.0-flash` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `google` | `models/gemini-2.0-flash-001` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `google` | `models/gemini-flash-latest` | 200 | invalid_json | {"is_ |
| `google` | `models/gemma-4-31b-it` | 200 | invalid_json | <thought>*   Product A: "PANADOL 20 TAB"     *   Product B: "PANADOL 20 TABLETS"      *   Brand: Panadol (Same)     *    |
| `github` | `openai/gpt-4o` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `xai/grok-3-mini` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `openai/gpt-5-chat` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `openai/gpt-5-mini` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `mistral-ai/mistral-medium-2505` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/meta/llama-3-8b-instruct` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/meta/llama-3-8b-instruct was deprecated on 2026-05-30. Se |
| `github` | `meta/llama-4-maverick-17b-128e-instruct-fp8` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `cloudflare` | `@cf/meta/llama-3-8b-instruct-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/meta/llama-3-8b-instruct-awq was deprecated on 2026-05-30 |
| `github` | `microsoft/phi-4-reasoning` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `microsoft/phi-4` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@cf/meta/llama-3.2-1b-instruct` | 200 | invalid_json | A simple string comparison.  Yes, A and B are the same product. |
| `github` | `openai/o4-mini` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@cf/deepseek-ai/deepseek-math-7b-instruct` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/deepseek-ai/deepseek-math-7b-instruct was deprecated on 2 |
| `github` | `openai/o3-mini` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@cf/zai-org/glm-4.7-flash` | 200 | invalid_json |  |
| `github` | `openai/o1-mini` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `cohere/cohere-command-r-plus-08-2024` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@cf/qwen/qwen1.5-14b-chat-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/qwen/qwen1.5-14b-chat-awq was deprecated on 2025-10-01. S |
| `github` | `mistral-ai/mistral-small-2503` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@cf/qwen/qwen1.5-7b-chat-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/qwen/qwen1.5-7b-chat-awq was deprecated on 2025-10-01. Se |
| `github` | `openai/gpt-4.1-mini` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@cf/openchat/openchat-3.5-0106` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/openchat/openchat-3.5-0106 was deprecated on 2025-10-01.  |
| `cloudflare` | `@cf/meta/llama-2-7b-chat-fp16` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/meta/llama-2-7b-chat-fp16 was deprecated on 2026-05-30. S |
| `cloudflare` | `@cf/meta/llama-2-7b-chat-int8` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/meta/llama-3-8b-instruct-awq was deprecated on 2026-05-30 |
| `cloudflare` | `@cf/microsoft/phi-2` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/microsoft/phi-2 was deprecated on 2026-05-30. See the mod |
| `cloudflare` | `@cf/qwen/qwen1.5-1.8b-chat` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/qwen/qwen1.5-1.8b-chat was deprecated on 2025-10-01. See  |
| `cloudflare` | `@cf/qwen/qwen1.5-0.5b-chat` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/qwen/qwen1.5-0.5b-chat was deprecated on 2025-10-01. See  |
| `cloudflare` | `@cf/tinyllama/tinyllama-1.1b-chat-v1.0` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/tinyllama/tinyllama-1.1b-chat-v1.0 was deprecated on 2025 |
| `cloudflare` | `@cf/tiiuae/falcon-7b-instruct` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/tiiuae/falcon-7b-instruct was deprecated on 2025-10-01. S |
| `cerebras` | `llama3.1-8b` | 404 | http_404 | {"message":"Model does not exist or you do not have access to it.","type":"not_found_error","param":"model","code":"mode |
| `opencode` | `trinity-large-preview-free` | 401 | http_401 | {"type":"error","error":{"type":"ModelError","message":"Model trinity-large-preview-free is not supported"}} |
| `groq` | `groq/compound-mini` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `opencode` | `hy3-preview-free` | 401 | http_401 | {"type":"error","error":{"type":"ModelError","message":"Model hy3-preview-free is not supported"}} |
| `groq` | `llama-3.1-8b-instant` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `groq` | `allam-2-7b` | 403 | http_403 | {"error":{"message":"Access denied. Please check your network settings."}} |
| `google` | `models/gemma-4-26b-a4b-it` | 200 | invalid_json | <thought>*   Product A: "PANADOL 20 TAB"     *   Product B: "PANADOL 20 TABLETS"     *   Goal: Determine if they are the |
| `google` | `models/gemini-2.0-flash-lite` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `google` | `models/gemini-2.0-flash-lite-001` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `google` | `models/gemini-pro-latest` | 429 | http_429 | [{   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing det |
| `github` | `openai/gpt-4o-mini` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `meta/llama-3.2-90b-vision-instruct` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `openai/gpt-5-nano` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `openai/gpt-4.1-nano` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `github` | `microsoft/phi-4-multimodal-instruct` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `github` | `meta/llama-3.2-11b-vision-instruct` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `github` | `microsoft/phi-4-mini-reasoning` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `github` | `mistral-ai/codestral-2501` | 410 | http_410 | {"error":{"code":"github_models_retirement_brownout","message":"GitHub Models is temporarily unavailable as part of a sc |
| `github` | `microsoft/phi-4-mini-instruct` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `github` | `cohere/cohere-command-r-08-2024` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@hf/nousresearch/hermes-2-pro-mistral-7b` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/nousresearch/hermes-2-pro-mistral-7b was deprecated on 20 |
| `github` | `meta/meta-llama-3.1-8b-instruct` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@hf/thebloke/llama-2-13b-chat-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/thebloke/llama-2-13b-chat-awq was deprecated on 2025-10-0 |
| `github` | `mistral-ai/ministral-3b` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@hf/thebloke/mistral-7b-instruct-v0.1-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/thebloke/mistral-7b-instruct-v0.1-awq was deprecated on 2 |
| `github` | `microsoft/mai-ds-r1` | 429 | http_429 | Too many requests. For more on scraping GitHub and how it may affect your rights, please review our Terms of Service (ht |
| `cloudflare` | `@hf/thebloke/neural-chat-7b-v3-1-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/thebloke/neural-chat-7b-v3-1-awq was deprecated on 2025-1 |
| `cloudflare` | `@hf/thebloke/openhermes-2.5-mistral-7b-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/thebloke/openhermes-2.5-mistral-7b-awq was deprecated on  |
| `cloudflare` | `@hf/thebloke/zephyr-7b-beta-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/thebloke/zephyr-7b-beta-awq was deprecated on 2025-10-01. |
| `cloudflare` | `@hf/nexusflow/starling-lm-7b-beta` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/nexusflow/starling-lm-7b-beta was deprecated on 2025-10-0 |
| `cloudflare` | `@hf/thebloke/deepseek-coder-6.7b-instruct-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/thebloke/deepseek-coder-6.7b-instruct-awq was deprecated  |
| `cloudflare` | `@cf/defog/sqlcoder-7b-2` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/defog/sqlcoder-7b-2 was deprecated on 2026-05-30. See the |
| `cloudflare` | `@cf/fblgit/una-cybertron-7b-v2-bf16` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/fblgit/una-cybertron-7b-v2-bf16 was deprecated on 2025-10 |
| `cloudflare` | `@cf/thebloke/discolm-german-7b-v1-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @cf/thebloke/discolm-german-7b-v1-awq was deprecated on 2025- |
| `cloudflare` | `@hf/thebloke/deepseek-coder-6.7b-base-awq` | 410 | http_410 | {"errors":[{"message":"AiError: Model has been deprecated: @hf/thebloke/deepseek-coder-6.7b-base-awq was deprecated on 2 |
| `cloudflare` | `@cf/meta-llama/llama-2-7b-chat-hf-lora` | 200 | invalid_json |  Heidelsocketeqnarrayzeg abroadrameaussian spatial(@ica films Tam уча supports GL morte Rosaágina oceanfalalter"/anelink |

## كل النماذج (النتيجة)

| مزوّد | Tier | النموذج | الحالة |
|---|---|---|---|
| `cerebras` | 1 | `gpt-oss-120b` | ❌ |
| `cerebras` | 2 | `llama-4-scout-17b-16e-instruct` | ❌ |
| `cerebras` | 3 | `llama3.1-8b` | ❌ |
| `cerebras` | 1 | `qwen-3-235b-a22b-instruct-2507` | ❌ |
| `cerebras` | 2 | `zai-glm-4.7` | ❌ |
| `cloudflare` | 1 | `@cf/aisingapore/gemma-sea-lion-v4-27b-it` | ✅ |
| `cloudflare` | 2 | `@cf/deepseek-ai/deepseek-math-7b-instruct` | ❌ |
| `cloudflare` | 1 | `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` | ❌ |
| `cloudflare` | 3 | `@cf/defog/sqlcoder-7b-2` | ❌ |
| `cloudflare` | 3 | `@cf/fblgit/una-cybertron-7b-v2-bf16` | ❌ |
| `cloudflare` | 3 | `@cf/google/gemma-2b-it-lora` | ✅ |
| `cloudflare` | 1 | `@cf/google/gemma-3-12b-it` | ❌ |
| `cloudflare` | 1 | `@cf/google/gemma-4-26b-a4b-it` | ❌ |
| `cloudflare` | 3 | `@cf/google/gemma-7b-it-lora` | ✅ |
| `cloudflare` | 1 | `@cf/ibm-granite/granite-4.0-h-micro` | ✅ |
| `cloudflare` | 3 | `@cf/meta-llama/llama-2-7b-chat-hf-lora` | ❌ |
| `cloudflare` | 2 | `@cf/meta/llama-2-7b-chat-fp16` | ❌ |
| `cloudflare` | 2 | `@cf/meta/llama-2-7b-chat-int8` | ❌ |
| `cloudflare` | 2 | `@cf/meta/llama-3-8b-instruct` | ❌ |
| `cloudflare` | 2 | `@cf/meta/llama-3-8b-instruct-awq` | ❌ |
| `cloudflare` | 1 | `@cf/meta/llama-3.1-8b-instruct-awq` | ❌ |
| `cloudflare` | 1 | `@cf/meta/llama-3.1-8b-instruct-fp8` | ✅ |
| `cloudflare` | 2 | `@cf/meta/llama-3.2-1b-instruct` | ❌ |
| `cloudflare` | 2 | `@cf/meta/llama-3.2-3b-instruct` | ✅ |
| `cloudflare` | 1 | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | ✅ |
| `cloudflare` | 1 | `@cf/meta/llama-4-scout-17b-16e-instruct` | ✅ |
| `cloudflare` | 2 | `@cf/microsoft/phi-2` | ❌ |
| `cloudflare` | 2 | `@cf/mistral/mistral-7b-instruct-v0.1` | ✅ |
| `cloudflare` | 3 | `@cf/mistral/mistral-7b-instruct-v0.2-lora` | ✅ |
| `cloudflare` | 1 | `@cf/mistralai/mistral-small-3.1-24b-instruct` | ✅ |
| `cloudflare` | 1 | `@cf/moonshotai/kimi-k2.5` | ❌ |
| `cloudflare` | 1 | `@cf/moonshotai/kimi-k2.6` | ❌ |
| `cloudflare` | 1 | `@cf/nvidia/nemotron-3-120b-a12b` | ❌ |
| `cloudflare` | 1 | `@cf/openai/gpt-oss-120b` | ❌ |
| `cloudflare` | 1 | `@cf/openai/gpt-oss-20b` | ❌ |
| `cloudflare` | 2 | `@cf/openchat/openchat-3.5-0106` | ❌ |
| `cloudflare` | 2 | `@cf/qwen/qwen1.5-0.5b-chat` | ❌ |
| `cloudflare` | 2 | `@cf/qwen/qwen1.5-1.8b-chat` | ❌ |
| `cloudflare` | 2 | `@cf/qwen/qwen1.5-14b-chat-awq` | ❌ |
| `cloudflare` | 2 | `@cf/qwen/qwen1.5-7b-chat-awq` | ❌ |
| `cloudflare` | 1 | `@cf/qwen/qwen2.5-coder-32b-instruct` | ❌ |
| `cloudflare` | 1 | `@cf/qwen/qwen3-30b-a3b-fp8` | ❌ |
| `cloudflare` | 1 | `@cf/qwen/qwq-32b` | ❌ |
| `cloudflare` | 3 | `@cf/thebloke/discolm-german-7b-v1-awq` | ❌ |
| `cloudflare` | 2 | `@cf/tiiuae/falcon-7b-instruct` | ❌ |
| `cloudflare` | 2 | `@cf/tinyllama/tinyllama-1.1b-chat-v1.0` | ❌ |
| `cloudflare` | 2 | `@cf/zai-org/glm-4.7-flash` | ❌ |
| `cloudflare` | 2 | `@hf/google/gemma-7b-it` | ✅ |
| `cloudflare` | 3 | `@hf/mistral/mistral-7b-instruct-v0.2` | ✅ |
| `cloudflare` | 3 | `@hf/nexusflow/starling-lm-7b-beta` | ❌ |
| `cloudflare` | 3 | `@hf/nousresearch/hermes-2-pro-mistral-7b` | ❌ |
| `cloudflare` | 3 | `@hf/thebloke/deepseek-coder-6.7b-base-awq` | ❌ |
| `cloudflare` | 3 | `@hf/thebloke/deepseek-coder-6.7b-instruct-awq` | ❌ |
| `cloudflare` | 3 | `@hf/thebloke/llama-2-13b-chat-awq` | ❌ |
| `cloudflare` | 3 | `@hf/thebloke/mistral-7b-instruct-v0.1-awq` | ❌ |
| `cloudflare` | 3 | `@hf/thebloke/neural-chat-7b-v3-1-awq` | ❌ |
| `cloudflare` | 3 | `@hf/thebloke/openhermes-2.5-mistral-7b-awq` | ❌ |
| `cloudflare` | 3 | `@hf/thebloke/zephyr-7b-beta-awq` | ❌ |
| `github` | 1 | `ai21-labs/ai21-jamba-1.5-large` | ❌ |
| `github` | 1 | `cohere/cohere-command-a` | ❌ |
| `github` | 3 | `cohere/cohere-command-r-08-2024` | ❌ |
| `github` | 2 | `cohere/cohere-command-r-plus-08-2024` | ❌ |
| `github` | 1 | `deepseek/deepseek-r1` | ❌ |
| `github` | 1 | `deepseek/deepseek-r1-0528` | ❌ |
| `github` | 1 | `deepseek/deepseek-v3-0324` | ❌ |
| `github` | 3 | `meta/llama-3.2-11b-vision-instruct` | ❌ |
| `github` | 3 | `meta/llama-3.2-90b-vision-instruct` | ❌ |
| `github` | 1 | `meta/llama-3.3-70b-instruct` | ❌ |
| `github` | 2 | `meta/llama-4-maverick-17b-128e-instruct-fp8` | ❌ |
| `github` | 1 | `meta/llama-4-scout-17b-16e-instruct` | ❌ |
| `github` | 1 | `meta/meta-llama-3.1-405b-instruct` | ❌ |
| `github` | 3 | `meta/meta-llama-3.1-8b-instruct` | ❌ |
| `github` | 3 | `microsoft/mai-ds-r1` | ❌ |
| `github` | 2 | `microsoft/phi-4` | ❌ |
| `github` | 3 | `microsoft/phi-4-mini-instruct` | ❌ |
| `github` | 3 | `microsoft/phi-4-mini-reasoning` | ❌ |
| `github` | 3 | `microsoft/phi-4-multimodal-instruct` | ❌ |
| `github` | 2 | `microsoft/phi-4-reasoning` | ❌ |
| `github` | 3 | `mistral-ai/codestral-2501` | ❌ |
| `github` | 3 | `mistral-ai/ministral-3b` | ❌ |
| `github` | 2 | `mistral-ai/mistral-medium-2505` | ❌ |
| `github` | 2 | `mistral-ai/mistral-small-2503` | ❌ |
| `github` | 1 | `openai/gpt-4.1` | ❌ |
| `github` | 2 | `openai/gpt-4.1-mini` | ❌ |
| `github` | 3 | `openai/gpt-4.1-nano` | ❌ |
| `github` | 2 | `openai/gpt-4o` | ❌ |
| `github` | 3 | `openai/gpt-4o-mini` | ❌ |
| `github` | 1 | `openai/gpt-5` | ❌ |
| `github` | 2 | `openai/gpt-5-chat` | ❌ |
| `github` | 2 | `openai/gpt-5-mini` | ❌ |
| `github` | 3 | `openai/gpt-5-nano` | ❌ |
| `github` | 1 | `openai/o1` | ❌ |
| `github` | 2 | `openai/o1-mini` | ❌ |
| `github` | 1 | `openai/o1-preview` | ❌ |
| `github` | 1 | `openai/o3` | ❌ |
| `github` | 2 | `openai/o3-mini` | ❌ |
| `github` | 2 | `openai/o4-mini` | ❌ |
| `github` | 1 | `xai/grok-3` | ❌ |
| `github` | 2 | `xai/grok-3-mini` | ❌ |
| `google` | 2 | `models/gemini-2.0-flash` | ❌ |
| `google` | 2 | `models/gemini-2.0-flash-001` | ❌ |
| `google` | 3 | `models/gemini-2.0-flash-lite` | ❌ |
| `google` | 3 | `models/gemini-2.0-flash-lite-001` | ❌ |
| `google` | 1 | `models/gemini-2.5-flash` | ❌ |
| `google` | 3 | `models/gemini-2.5-flash-lite` | ✅ |
| `google` | 1 | `models/gemini-2.5-pro` | ❌ |
| `google` | 2 | `models/gemini-3-flash-preview` | ❌ |
| `google` | 1 | `models/gemini-3-pro-preview` | ❌ |
| `google` | 2 | `models/gemini-3.1-flash-lite` | ✅ |
| `google` | 1 | `models/gemini-3.1-flash-lite-preview` | ✅ |
| `google` | 1 | `models/gemini-3.1-pro-preview` | ❌ |
| `google` | 1 | `models/gemini-3.1-pro-preview-customtools` | ❌ |
| `google` | 2 | `models/gemini-flash-latest` | ❌ |
| `google` | 3 | `models/gemini-flash-lite-latest` | ✅ |
| `google` | 3 | `models/gemini-pro-latest` | ❌ |
| `google` | 3 | `models/gemma-4-26b-a4b-it` | ❌ |
| `google` | 2 | `models/gemma-4-31b-it` | ❌ |
| `groq` | 3 | `allam-2-7b` | ❌ |
| `groq` | 2 | `groq/compound` | ❌ |
| `groq` | 3 | `groq/compound-mini` | ❌ |
| `groq` | 3 | `llama-3.1-8b-instant` | ❌ |
| `groq` | 2 | `llama-3.3-70b-versatile` | ❌ |
| `groq` | 1 | `meta-llama/llama-4-scout-17b-16e-instruct` | ❌ |
| `groq` | 1 | `openai/gpt-oss-120b` | ❌ |
| `groq` | 2 | `openai/gpt-oss-20b` | ❌ |
| `groq` | 1 | `qwen/qwen3-32b` | ❌ |
| `mistral` | 1 | `mistral-large-latest` | ✅ |
| `mistral` | 1 | `mistral-medium-latest` | ✅ |
| `mistral` | 2 | `mistral-small-latest` | ✅ |
| `mistral` | 2 | `open-mistral-7b` | ✅ |
| `mistral` | 3 | `open-mixtral-8x22b` | ✅ |
| `mistral` | 3 | `open-mixtral-8x7b` | ✅ |
| `opencode` | 1 | `big-pickle` | ✅ |
| `opencode` | 2 | `deepseek-v4-flash-free` | ❌ |
| `opencode` | 3 | `hy3-preview-free` | ❌ |
| `opencode` | 1 | `minimax-m2.5-free` | ❌ |
| `opencode` | 1 | `nemotron-3-super-free` | ❌ |
| `opencode` | 2 | `ring-2.6-1t-free` | ❌ |
| `opencode` | 3 | `trinity-large-preview-free` | ❌ |
| `openrouter` | 1 | `deepseek/deepseek-r1` | ❌ |
| `openrouter` | 3 | `meta-llama/llama-3.1-8b-instruct` | ✅ |
| `openrouter` | 2 | `meta-llama/llama-3.3-70b-instruct` | ✅ |
| `openrouter` | 1 | `meta-llama/llama-4-scout-17b-16e-instruct` | ✅ |
| `openrouter` | 2 | `openai/gpt-4o` | ✅ |
| `openrouter` | 3 | `openai/gpt-4o-mini` | ✅ |