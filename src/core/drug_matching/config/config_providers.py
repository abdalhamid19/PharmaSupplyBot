"""Provider configuration for AI API.

Stage 3 migrated the canonical per-provider metadata
(``base_url`` / ``env_keys`` / ``account_id_env``) into
``ai.providers.*`` of ``config.yaml`` via
:class:`src.core.drug_matching.config.ProviderMetadata` /
:func:`src.core.drug_matching.config.get_provider_metadata`.

This module is preserved as the **backward-compatibility shim**:

  * :data:`PROVIDERS` is now a thin alias over
    :data:`src.core.drug_matching.config._FALLBACK_PROVIDER_METADATA`,
    re-shaped into the historical ``dict[str, dict]`` layout that
    external tests and third-party callers may still rely on.
  * :func:`provider_base_url` and :func:`cloudflare_base_url` stay
    in place because :mod:`src.core.drug_matching.config.config_helpers`
    uses them as a final fallback when ``ai.providers.<name>.*`` is
    absent.

New code should consume
:func:`src.core.drug_matching.config.get_provider_metadata` directly
and read :class:`~src.core.drug_matching.config.ProviderMetadata`
fields — both types live in ``config_models.py``.
"""

from __future__ import annotations

import os


def cloudflare_base_url(account_id: str) -> str:
    """Return the OpenAI-compatible Cloudflare Workers AI URL."""
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id.strip()}/ai/v1"


def provider_base_url(info: dict) -> str:
    """Return a provider base URL, including Cloudflare account URL expansion.

    Kept for backward compatibility with callers that still pass a
    dict shaped like the historical :data:`PROVIDERS` entry.
    """
    account_id = os.getenv(info.get("account_id_env", ""), "").strip()
    if account_id:
        return cloudflare_base_url(account_id)
    url = os.getenv(info.get("base_url_env", ""), "").strip() or info.get("base_url", "")
    return "" if "<" in url or ">" in url else url


#: Backward-compatible alias over the hardcoded fallback metadata.
#: Shape mirrors the legacy dict layout so legacy test snapshots still
#: pass — consumers should migrate to
#: :func:`src.core.drug_matching.config.get_provider_metadata`.
def _build_providers_alias() -> dict:
    from .config_models import _FALLBACK_PROVIDER_METADATA  # local import

    out: dict = {}
    for name, meta in _FALLBACK_PROVIDER_METADATA.items():
        entry: dict[str, object] = {
            "base_url": meta.base_url,
            "env_keys": meta.env_keys,
            "env_key": meta.env_keys[0] if meta.env_keys else "",
            "default_model": "",
        }
        if meta.account_id_env:
            entry["account_id_env"] = meta.account_id_env
        out[name] = entry
    # Pseudo-providers that have no metadata of their own.
    out["rotation"] = {"base_url": "", "env_keys": (), "env_key": "", "default_model": ""}
    out.setdefault("custom", {"base_url": "", "env_keys": (), "env_key": "CUSTOM_API_KEY", "default_model": ""})
    return out


PROVIDERS: dict = _build_providers_alias()


__all__ = ["PROVIDERS", "provider_base_url", "cloudflare_base_url"]
