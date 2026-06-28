"""Provider configuration for AI API."""

from __future__ import annotations

import os


PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "env_keys": ("OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY"),
        "default_model": "openai/gpt-4o-mini",
    },
    "opencode": {
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_API_KEY",
        "env_keys": ("OPENCODE_API_KEY_1", "OPENCODE_API_KEY"),
        "default_model": "big-pickle",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "env_keys": ("GROQ_API_KEY_1", "GROQ_API_KEY"),
        "default_model": "openai/gpt-oss-120b",
    },
    "github": {
        "base_url": "https://models.github.ai/inference",
        "env_key": "GITHUB_API_KEY",
        "env_keys": ("GITHUB_API_KEY_1", "GITHUB_API_KEY"),
        "default_model": "openai/gpt-4.1-mini",
    },
    "cloudflare": {
        "base_url": "",
        "base_url_env": "CLOUDFLARE_BASE_URL",
        "account_id_env": "CLOUDFLARE_ACCOUNT_ID",
        "env_key": "CLOUDFLARE_API_TOKEN",
        "env_keys": ("CLOUDFLARE_API_TOKEN_1", "CLOUDFLARE_API_TOKEN"),
        "default_model": "@cf/openai/gpt-oss-120b",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "env_key": "CEREBRAS_API_KEY",
        "env_keys": ("CEREBRAS_API_KEY_1", "CEREBRAS_API_KEY"),
        "default_model": "gpt-oss-120b",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GOOGLE_API_KEY",
        "env_keys": ("GOOGLE_API_KEY_1", "GOOGLE_API_KEY"),
        "default_model": "gemini-2.5-flash",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "env_key": "MISTRAL_API_KEY",
        "env_keys": ("MISTRAL_API_KEY_1", "MISTRAL_API_KEY"),
        "default_model": "mistral-small-latest",
    },
    "rotation": {"base_url": "", "env_key": "", "env_keys": (), "default_model": ""},
    "custom": {
        "base_url": "",
        "env_key": "CUSTOM_API_KEY",
        "env_keys": ("CUSTOM_API_KEY",),
        "default_model": "",
    },
}


def provider_base_url(info: dict) -> str:
    """Return a provider base URL, including Cloudflare account URL expansion."""
    account_id = os.getenv(info.get("account_id_env", ""), "").strip()
    if account_id:
        return cloudflare_base_url(account_id)
    url = os.getenv(info.get("base_url_env", ""), "").strip() or info["base_url"]
    return "" if "<" in url or ">" in url else url


def cloudflare_base_url(account_id: str) -> str:
    """Return the OpenAI-compatible Cloudflare Workers AI URL."""
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id.strip()}/ai/v1"


__all__ = ["PROVIDERS", "provider_base_url", "cloudflare_base_url"]
