# تقرير استكشاف نماذج الذكاء الاصطناعي وترتيبها (Tiers)

## نظرة عامة

| القياس | القيمة |
|---|---|
| إجمالي المحاولات (attempts) | **834** |
| المفتاحـُ الواجب توافره | **يقرأ من `.env` عبر dotenv** |
| عدد مزوّدي الخدمة | **8** |
| النماذج الفريدة الإجمالية | **145** |

### توزيع النماذج الفريدة حسب الـ Tier

| Tier | الوصف | عدد النماذج |
|---|---|---|
| **Tier 1** | الأقوى (أول ثُلث لكل قائمة) | 50 |
| **Tier 2** | المتوسط | 49 |
| **Tier 3** | الأضعف (آخر ثُلث) | 46 |

> يُحسب الـ tier لكل نموذج من ترتيبه داخل قائمة نماذج المزوّد
> (مع `_model_tier` في `ai_rotation.py`) — تقسيم متساوي لثلاثة أثلاث.

## `cerebras`

- **النماذج الفريدة**: 5

| Tier | النموذج |
|---|------|
| ✅ **Tier 1** | `gpt-oss-120b` |
| ⚠️ **Tier 2** | `llama-4-scout-17b-16e-instruct` |
| ❌ **Tier 3** | `llama3.1-8b` |
| ✅ **Tier 1** | `qwen-3-235b-a22b-instruct-2507` |
| ⚠️ **Tier 2** | `zai-glm-4.7` |

## `cloudflare`

- **النماذج الفريدة**: 53

| Tier | النموذج |
|---|------|
| ✅ **Tier 1** | `@cf/aisingapore/gemma-sea-lion-v4-27b-it` |
| ⚠️ **Tier 2** | `@cf/deepseek-ai/deepseek-math-7b-instruct` |
| ✅ **Tier 1** | `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` |
| ❌ **Tier 3** | `@cf/defog/sqlcoder-7b-2` |
| ❌ **Tier 3** | `@cf/fblgit/una-cybertron-7b-v2-bf16` |
| ❌ **Tier 3** | `@cf/google/gemma-2b-it-lora` |
| ✅ **Tier 1** | `@cf/google/gemma-3-12b-it` |
| ✅ **Tier 1** | `@cf/google/gemma-4-26b-a4b-it` |
| ❌ **Tier 3** | `@cf/google/gemma-7b-it-lora` |
| ✅ **Tier 1** | `@cf/ibm-granite/granite-4.0-h-micro` |
| ❌ **Tier 3** | `@cf/meta-llama/llama-2-7b-chat-hf-lora` |
| ⚠️ **Tier 2** | `@cf/meta/llama-2-7b-chat-fp16` |
| ⚠️ **Tier 2** | `@cf/meta/llama-2-7b-chat-int8` |
| ⚠️ **Tier 2** | `@cf/meta/llama-3-8b-instruct` |
| ⚠️ **Tier 2** | `@cf/meta/llama-3-8b-instruct-awq` |
| ✅ **Tier 1** | `@cf/meta/llama-3.1-8b-instruct-awq` |
| ✅ **Tier 1** | `@cf/meta/llama-3.1-8b-instruct-fp8` |
| ⚠️ **Tier 2** | `@cf/meta/llama-3.2-1b-instruct` |
| ⚠️ **Tier 2** | `@cf/meta/llama-3.2-3b-instruct` |
| ✅ **Tier 1** | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` |
| ✅ **Tier 1** | `@cf/meta/llama-4-scout-17b-16e-instruct` |
| ⚠️ **Tier 2** | `@cf/microsoft/phi-2` |
| ⚠️ **Tier 2** | `@cf/mistral/mistral-7b-instruct-v0.1` |
| ❌ **Tier 3** | `@cf/mistral/mistral-7b-instruct-v0.2-lora` |
| ✅ **Tier 1** | `@cf/mistralai/mistral-small-3.1-24b-instruct` |
| ✅ **Tier 1** | `@cf/moonshotai/kimi-k2.5` |
| ✅ **Tier 1** | `@cf/moonshotai/kimi-k2.6` |
| ✅ **Tier 1** | `@cf/nvidia/nemotron-3-120b-a12b` |
| ✅ **Tier 1** | `@cf/openai/gpt-oss-120b` |
| ✅ **Tier 1** | `@cf/openai/gpt-oss-20b` |
| ⚠️ **Tier 2** | `@cf/openchat/openchat-3.5-0106` |
| ⚠️ **Tier 2** | `@cf/qwen/qwen1.5-0.5b-chat` |
| ⚠️ **Tier 2** | `@cf/qwen/qwen1.5-1.8b-chat` |
| ⚠️ **Tier 2** | `@cf/qwen/qwen1.5-14b-chat-awq` |
| ⚠️ **Tier 2** | `@cf/qwen/qwen1.5-7b-chat-awq` |
| ✅ **Tier 1** | `@cf/qwen/qwen2.5-coder-32b-instruct` |
| ✅ **Tier 1** | `@cf/qwen/qwen3-30b-a3b-fp8` |
| ✅ **Tier 1** | `@cf/qwen/qwq-32b` |
| ❌ **Tier 3** | `@cf/thebloke/discolm-german-7b-v1-awq` |
| ⚠️ **Tier 2** | `@cf/tiiuae/falcon-7b-instruct` |
| ⚠️ **Tier 2** | `@cf/tinyllama/tinyllama-1.1b-chat-v1.0` |
| ⚠️ **Tier 2** | `@cf/zai-org/glm-4.7-flash` |
| ⚠️ **Tier 2** | `@hf/google/gemma-7b-it` |
| ❌ **Tier 3** | `@hf/mistral/mistral-7b-instruct-v0.2` |
| ❌ **Tier 3** | `@hf/nexusflow/starling-lm-7b-beta` |
| ❌ **Tier 3** | `@hf/nousresearch/hermes-2-pro-mistral-7b` |
| ❌ **Tier 3** | `@hf/thebloke/deepseek-coder-6.7b-base-awq` |
| ❌ **Tier 3** | `@hf/thebloke/deepseek-coder-6.7b-instruct-awq` |
| ❌ **Tier 3** | `@hf/thebloke/llama-2-13b-chat-awq` |
| ❌ **Tier 3** | `@hf/thebloke/mistral-7b-instruct-v0.1-awq` |
| ❌ **Tier 3** | `@hf/thebloke/neural-chat-7b-v3-1-awq` |
| ❌ **Tier 3** | `@hf/thebloke/openhermes-2.5-mistral-7b-awq` |
| ❌ **Tier 3** | `@hf/thebloke/zephyr-7b-beta-awq` |

## `github`

- **النماذج الفريدة**: 41

| Tier | النموذج |
|---|------|
| ✅ **Tier 1** | `ai21-labs/ai21-jamba-1.5-large` |
| ✅ **Tier 1** | `cohere/cohere-command-a` |
| ❌ **Tier 3** | `cohere/cohere-command-r-08-2024` |
| ⚠️ **Tier 2** | `cohere/cohere-command-r-plus-08-2024` |
| ✅ **Tier 1** | `deepseek/deepseek-r1` |
| ✅ **Tier 1** | `deepseek/deepseek-r1-0528` |
| ✅ **Tier 1** | `deepseek/deepseek-v3-0324` |
| ❌ **Tier 3** | `meta/llama-3.2-11b-vision-instruct` |
| ❌ **Tier 3** | `meta/llama-3.2-90b-vision-instruct` |
| ✅ **Tier 1** | `meta/llama-3.3-70b-instruct` |
| ⚠️ **Tier 2** | `meta/llama-4-maverick-17b-128e-instruct-fp8` |
| ✅ **Tier 1** | `meta/llama-4-scout-17b-16e-instruct` |
| ✅ **Tier 1** | `meta/meta-llama-3.1-405b-instruct` |
| ❌ **Tier 3** | `meta/meta-llama-3.1-8b-instruct` |
| ❌ **Tier 3** | `microsoft/mai-ds-r1` |
| ⚠️ **Tier 2** | `microsoft/phi-4` |
| ❌ **Tier 3** | `microsoft/phi-4-mini-instruct` |
| ❌ **Tier 3** | `microsoft/phi-4-mini-reasoning` |
| ❌ **Tier 3** | `microsoft/phi-4-multimodal-instruct` |
| ⚠️ **Tier 2** | `microsoft/phi-4-reasoning` |
| ❌ **Tier 3** | `mistral-ai/codestral-2501` |
| ❌ **Tier 3** | `mistral-ai/ministral-3b` |
| ⚠️ **Tier 2** | `mistral-ai/mistral-medium-2505` |
| ⚠️ **Tier 2** | `mistral-ai/mistral-small-2503` |
| ✅ **Tier 1** | `openai/gpt-4.1` |
| ⚠️ **Tier 2** | `openai/gpt-4.1-mini` |
| ❌ **Tier 3** | `openai/gpt-4.1-nano` |
| ⚠️ **Tier 2** | `openai/gpt-4o` |
| ❌ **Tier 3** | `openai/gpt-4o-mini` |
| ✅ **Tier 1** | `openai/gpt-5` |
| ⚠️ **Tier 2** | `openai/gpt-5-chat` |
| ⚠️ **Tier 2** | `openai/gpt-5-mini` |
| ❌ **Tier 3** | `openai/gpt-5-nano` |
| ✅ **Tier 1** | `openai/o1` |
| ⚠️ **Tier 2** | `openai/o1-mini` |
| ✅ **Tier 1** | `openai/o1-preview` |
| ✅ **Tier 1** | `openai/o3` |
| ⚠️ **Tier 2** | `openai/o3-mini` |
| ⚠️ **Tier 2** | `openai/o4-mini` |
| ✅ **Tier 1** | `xai/grok-3` |
| ⚠️ **Tier 2** | `xai/grok-3-mini` |

## `google`

- **النماذج الفريدة**: 18

| Tier | النموذج |
|---|------|
| ⚠️ **Tier 2** | `models/gemini-2.0-flash` |
| ⚠️ **Tier 2** | `models/gemini-2.0-flash-001` |
| ❌ **Tier 3** | `models/gemini-2.0-flash-lite` |
| ❌ **Tier 3** | `models/gemini-2.0-flash-lite-001` |
| ✅ **Tier 1** | `models/gemini-2.5-flash` |
| ❌ **Tier 3** | `models/gemini-2.5-flash-lite` |
| ✅ **Tier 1** | `models/gemini-2.5-pro` |
| ⚠️ **Tier 2** | `models/gemini-3-flash-preview` |
| ✅ **Tier 1** | `models/gemini-3-pro-preview` |
| ⚠️ **Tier 2** | `models/gemini-3.1-flash-lite` |
| ✅ **Tier 1** | `models/gemini-3.1-flash-lite-preview` |
| ✅ **Tier 1** | `models/gemini-3.1-pro-preview` |
| ✅ **Tier 1** | `models/gemini-3.1-pro-preview-customtools` |
| ⚠️ **Tier 2** | `models/gemini-flash-latest` |
| ❌ **Tier 3** | `models/gemini-flash-lite-latest` |
| ❌ **Tier 3** | `models/gemini-pro-latest` |
| ❌ **Tier 3** | `models/gemma-4-26b-a4b-it` |
| ⚠️ **Tier 2** | `models/gemma-4-31b-it` |

## `groq`

- **النماذج الفريدة**: 9

| Tier | النموذج |
|---|------|
| ❌ **Tier 3** | `allam-2-7b` |
| ⚠️ **Tier 2** | `groq/compound` |
| ❌ **Tier 3** | `groq/compound-mini` |
| ❌ **Tier 3** | `llama-3.1-8b-instant` |
| ⚠️ **Tier 2** | `llama-3.3-70b-versatile` |
| ✅ **Tier 1** | `meta-llama/llama-4-scout-17b-16e-instruct` |
| ✅ **Tier 1** | `openai/gpt-oss-120b` |
| ⚠️ **Tier 2** | `openai/gpt-oss-20b` |
| ✅ **Tier 1** | `qwen/qwen3-32b` |

## `mistral`

- **النماذج الفريدة**: 6

| Tier | النموذج |
|---|------|
| ✅ **Tier 1** | `mistral-large-latest` |
| ✅ **Tier 1** | `mistral-medium-latest` |
| ⚠️ **Tier 2** | `mistral-small-latest` |
| ⚠️ **Tier 2** | `open-mistral-7b` |
| ❌ **Tier 3** | `open-mixtral-8x22b` |
| ❌ **Tier 3** | `open-mixtral-8x7b` |

## `opencode`

- **النماذج الفريدة**: 7

| Tier | النموذج |
|---|------|
| ✅ **Tier 1** | `big-pickle` |
| ⚠️ **Tier 2** | `deepseek-v4-flash-free` |
| ❌ **Tier 3** | `hy3-preview-free` |
| ✅ **Tier 1** | `minimax-m2.5-free` |
| ✅ **Tier 1** | `nemotron-3-super-free` |
| ⚠️ **Tier 2** | `ring-2.6-1t-free` |
| ❌ **Tier 3** | `trinity-large-preview-free` |

## `openrouter`

- **النماذج الفريدة**: 6

| Tier | النموذج |
|---|------|
| ✅ **Tier 1** | `deepseek/deepseek-r1` |
| ❌ **Tier 3** | `meta-llama/llama-3.1-8b-instruct` |
| ⚠️ **Tier 2** | `meta-llama/llama-3.3-70b-instruct` |
| ✅ **Tier 1** | `meta-llama/llama-4-scout-17b-16e-instruct` |
| ⚠️ **Tier 2** | `openai/gpt-4o` |
| ❌ **Tier 3** | `openai/gpt-4o-mini` |

---

## كيف يُحسب الـ Tier لكل نموذج؟

```python
def _model_tier(rank, model_count):
    if model_count <= 0: return 3
    first_end  = (model_count + 2) // 3
    second_end = (model_count * 2 + 2) // 3
    return 1 if rank <= first_end else 2 if rank <= second_end else 3
```

أي الترتيب `rank` (1-indexed) للنموذج داخل قائمة
`ai.providers.<name>.models` من `config.yaml`.