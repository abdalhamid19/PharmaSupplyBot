"""Provider/model rotation planning for AI calls."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .ai_health import dedupe, mask_key, split_csv
from .config import PROVIDERS, cloudflare_base_url, provider_base_url

PROVIDER_ORDER = (
    "groq",
    "opencode",
    "openrouter",
    "github",
    "cerebras",
    "google",
    "mistral",
    "cloudflare",
)

DEFAULT_MODELS = {
    "groq": (
        "openai/gpt-oss-120b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "qwen/qwen3-32b",
        "llama-3.3-70b-versatile",
        "groq/compound",
        "openai/gpt-oss-20b",
        "groq/compound-mini",
        "llama-3.1-8b-instant",
        "allam-2-7b",
    ),
    "opencode": (
        "big-pickle",
        "nemotron-3-super-free",
        "minimax-m2.5-free",
        "deepseek-v4-flash-free",
        "ring-2.6-1t-free",
        "trinity-large-preview-free",
        "hy3-preview-free",
    ),
    "openrouter": (
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "inclusionai/ring-2.6-1t:free",
        "openai/gpt-oss-120b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "minimax/minimax-m2.5:free",
        "arcee-ai/trinity-large-thinking:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "google/gemma-4-31b-it:free",
        "openai/gpt-oss-20b:free",
        "z-ai/glm-4.5-air:free",
        "qwen/qwen3-coder:free",
        "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
        "google/gemma-4-26b-a4b-it:free",
        "poolside/laguna-m.1:free",
        "baidu/cobuddy:free",
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "nvidia/nemotron-nano-9b-v2:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "poolside/laguna-xs.2:free",
        "baidu/qianfan-ocr-fast:free",
        "liquid/lfm-2.5-1.2b-thinking:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "openrouter/owl-alpha",
        "openrouter/free",
    ),
    "github": (
        "meta/meta-llama-3.1-405b-instruct",
        "deepseek/deepseek-r1-0528",
        "deepseek/deepseek-r1",
        "deepseek/deepseek-v3-0324",
        "xai/grok-3",
        "meta/llama-4-scout-17b-16e-instruct",
        "openai/gpt-5",
        "openai/o3",
        "openai/o1",
        "openai/o1-preview",
        "meta/llama-3.3-70b-instruct",
        "ai21-labs/ai21-jamba-1.5-large",
        "cohere/cohere-command-a",
        "openai/gpt-4.1",
        "openai/gpt-4o",
        "xai/grok-3-mini",
        "openai/gpt-5-chat",
        "openai/gpt-5-mini",
        "mistral-ai/mistral-medium-2505",
        "meta/llama-4-maverick-17b-128e-instruct-fp8",
        "microsoft/phi-4-reasoning",
        "microsoft/phi-4",
        "openai/o4-mini",
        "openai/o3-mini",
        "openai/o1-mini",
        "cohere/cohere-command-r-plus-08-2024",
        "mistral-ai/mistral-small-2503",
        "openai/gpt-4.1-mini",
        "openai/gpt-4o-mini",
        "meta/llama-3.2-90b-vision-instruct",
        "openai/gpt-5-nano",
        "openai/gpt-4.1-nano",
        "microsoft/phi-4-multimodal-instruct",
        "meta/llama-3.2-11b-vision-instruct",
        "microsoft/phi-4-mini-reasoning",
        "mistral-ai/codestral-2501",
        "microsoft/phi-4-mini-instruct",
        "cohere/cohere-command-r-08-2024",
        "meta/meta-llama-3.1-8b-instruct",
        "mistral-ai/ministral-3b",
        "microsoft/mai-ds-r1",
    ),
    "cerebras": (
        "qwen-3-235b-a22b-instruct-2507",
        "gpt-oss-120b",
        "zai-glm-4.7",
        "llama-4-scout-17b-16e-instruct",
        "llama3.1-8b",
    ),
    "google": (
        "models/gemini-2.5-pro",
        "models/gemini-3.1-pro-preview",
        "models/gemini-3.1-pro-preview-customtools",
        "models/gemini-3-pro-preview",
        "models/gemini-2.5-flash",
        "models/gemini-3.1-flash-lite-preview",
        "models/gemini-3.1-flash-lite",
        "models/gemini-3-flash-preview",
        "models/gemini-2.0-flash",
        "models/gemini-2.0-flash-001",
        "models/gemini-flash-latest",
        "models/gemma-4-31b-it",
        "models/gemma-4-26b-a4b-it",
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.0-flash-lite",
        "models/gemini-2.0-flash-lite-001",
        "models/gemini-flash-lite-latest",
        "models/gemini-pro-latest",
    ),
    "mistral": (
        "mistral-small-latest",
        "mistral-small-2603",
        "mistral-small-2506",
        "codestral-latest",
        "codestral-2508",
        "ministral-14b-latest",
        "ministral-14b-2512",
        "ministral-8b-latest",
        "ministral-8b-2512",
        "ministral-3b-latest",
        "ministral-3b-2512",
    ),
    "cloudflare": (
        "@cf/openai/gpt-oss-120b",
        "@cf/nvidia/nemotron-3-120b-a12b",
        "@cf/moonshotai/kimi-k2.6",
        "@cf/moonshotai/kimi-k2.5",
        "@cf/meta/llama-4-scout-17b-16e-instruct",
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "@cf/qwen/qwen3-30b-a3b-fp8",
        "@cf/qwen/qwq-32b",
        "@cf/google/gemma-4-26b-a4b-it",
        "@cf/mistralai/mistral-small-3.1-24b-instruct",
        "@cf/qwen/qwen2.5-coder-32b-instruct",
        "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
        "@cf/aisingapore/gemma-sea-lion-v4-27b-it",
        "@cf/ibm-granite/granite-4.0-h-micro",
        "@cf/google/gemma-3-12b-it",
        "@cf/openai/gpt-oss-20b",
        "@cf/meta/llama-3.1-8b-instruct-fp8",
        "@cf/meta/llama-3.1-8b-instruct-awq",
        "@cf/meta/llama-3-8b-instruct",
        "@cf/meta/llama-3-8b-instruct-awq",
        "@cf/meta/llama-3.2-3b-instruct",
        "@cf/meta/llama-3.2-1b-instruct",
        "@cf/deepseek-ai/deepseek-math-7b-instruct",
        "@cf/zai-org/glm-4.7-flash",
        "@cf/mistral/mistral-7b-instruct-v0.1",
        "@cf/qwen/qwen1.5-14b-chat-awq",
        "@cf/qwen/qwen1.5-7b-chat-awq",
        "@cf/openchat/openchat-3.5-0106",
        "@cf/meta/llama-2-7b-chat-fp16",
        "@cf/meta/llama-2-7b-chat-int8",
        "@cf/microsoft/phi-2",
        "@cf/qwen/qwen1.5-1.8b-chat",
        "@cf/qwen/qwen1.5-0.5b-chat",
        "@cf/tinyllama/tinyllama-1.1b-chat-v1.0",
        "@cf/tiiuae/falcon-7b-instruct",
        "@hf/google/gemma-7b-it",
        "@hf/mistral/mistral-7b-instruct-v0.2",
        "@hf/nousresearch/hermes-2-pro-mistral-7b",
        "@hf/thebloke/llama-2-13b-chat-awq",
        "@hf/thebloke/mistral-7b-instruct-v0.1-awq",
        "@hf/thebloke/neural-chat-7b-v3-1-awq",
        "@hf/thebloke/openhermes-2.5-mistral-7b-awq",
        "@hf/thebloke/zephyr-7b-beta-awq",
        "@hf/nexusflow/starling-lm-7b-beta",
        "@hf/thebloke/deepseek-coder-6.7b-instruct-awq",
        "@cf/defog/sqlcoder-7b-2",
        "@cf/fblgit/una-cybertron-7b-v2-bf16",
        "@cf/thebloke/discolm-german-7b-v1-awq",
        "@hf/thebloke/deepseek-coder-6.7b-base-awq",
        "@cf/mistral/mistral-7b-instruct-v0.2-lora",
        "@cf/google/gemma-7b-it-lora",
        "@cf/google/gemma-2b-it-lora",
        "@cf/meta-llama/llama-2-7b-chat-hf-lora",
    ),
}


@dataclass(frozen=True, slots=True)
class AIModelAttempt:
    provider: str
    base_url: str
    key_name: str
    api_key: str = field(repr=False)
    model: str
    quality_rank: int
    latency: float = 9999.0
    quota_remaining: float = 0.0
    eligible: bool = True
    disabled_until: str = ""
    rotation_tier: int = 1

    @property
    def key_suffix(self) -> str:
        return self.api_key[-6:] if self.api_key else ""

    @property
    def key_masked(self) -> str:
        return mask_key(self.api_key)

    def safe_tuple(self) -> tuple[str, str, str]:
        return self.provider, self.key_suffix, self.model


def configured_attempts(providers: str = "auto") -> tuple[AIModelAttempt, ...]:
    selected = _selected_providers(providers)
    attempts: list[AIModelAttempt] = []
    for provider in selected:
        attempts.extend(_provider_attempts(provider))
    return tuple(rank_attempts(attempts))


def rank_attempts(attempts) -> list[AIModelAttempt]:
    return sorted(attempts, key=_balanced_sort_key)


def _balanced_sort_key(attempt: AIModelAttempt):
    quota_sort = -attempt.quota_remaining if attempt.quota_remaining else 0
    return (
        not attempt.eligible,
        bool(attempt.disabled_until),
        attempt.rotation_tier,
        attempt.quality_rank,
        quota_sort,
        attempt.latency,
        PROVIDER_ORDER.index(attempt.provider)
        if attempt.provider in PROVIDER_ORDER else len(PROVIDER_ORDER),
    )


def _selected_providers(value: str) -> tuple[str, ...]:
    if not value or value == "auto":
        return PROVIDER_ORDER
    requested = tuple(p.strip() for p in value.split(",") if p.strip())
    return tuple(p for p in requested if p in PROVIDERS and p != "rotation")


def _provider_attempts(provider: str) -> list[AIModelAttempt]:
    info = PROVIDERS.get(provider, {})
    keys = _provider_keys(provider, info)
    models = _provider_models(provider, info)
    attempts = []
    model_count = len(models)
    for key_name, key_value in keys:
        base_url = _provider_base_url(provider, info, key_name)
        if not base_url:
            continue
        for rank, model in enumerate(models, start=1):
            attempts.append(
                AIModelAttempt(
                    provider=provider,
                    base_url=base_url,
                    key_name=key_name,
                    api_key=key_value,
                    model=model,
                    quality_rank=rank,
                    rotation_tier=_model_tier(rank, model_count),
                )
            )
    return attempts


def _model_tier(rank: int, model_count: int) -> int:
    if model_count <= 0:
        return 3
    first_end = (model_count + 2) // 3
    second_end = (model_count * 2 + 2) // 3
    if rank <= first_end:
        return 1
    if rank <= second_end:
        return 2
    return 3


def _cloudflare_account_ids(info: dict) -> dict[str, str]:
    account_id_envs = info.get("account_id_envs", ())
    return {
        key_env: os.getenv(account_env, "").strip()
        for key_env, account_env in zip(info.get("env_keys", ()), account_id_envs)
        if os.getenv(account_env, "").strip()
    }


def _provider_base_url(provider: str, info: dict, key_name: str) -> str:
    if provider == "cloudflare":
        account_id = _cloudflare_account_ids(info).get(key_name, "")
        if account_id:
            return cloudflare_base_url(account_id)
    return provider_base_url(info)


def _provider_keys(provider: str, info: dict) -> list[tuple[str, str]]:
    keys = []
    for env_name in info.get("env_keys", ()):
        value = os.getenv(env_name, "").strip()
        if value:
            keys.append((env_name, value))
    seen = set()
    out = []
    for item in keys:
        if item[1] not in seen:
            seen.add(item[1])
            out.append(item)
    return out


def _provider_models(provider: str, info: dict) -> list[str]:
    env_name = f"{provider.upper()}_MODELS"
    env_models = split_csv(os.getenv(env_name, ""))
    defaults = list(DEFAULT_MODELS.get(provider, ()))
    if not defaults and info.get("default_model"):
        defaults = [info["default_model"]]
    return dedupe(env_models + defaults)
