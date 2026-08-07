"""Live model discovery for AI providers.

Queries each configured provider's OpenAI-compatible ``/models``
endpoint and reports which models actually exist on the remote side,
so operators can see the real catalog instead of the hand-curated
``ai.providers.*.models`` list in ``config.yaml``.

Design notes:

* Reuses the credential/base-URL resolution from
  :mod:`src.core.drug_matching.ai.ai_rotation` (``_resolve_meta`` /
  ``_provider_keys`` / ``_provider_base_url``) so discovery sees the
  exact same keys and endpoints as the rotation plan.
* One HTTP request per provider (first available key), not per model —
  the ``/models`` endpoint returns the whole catalog in one call.
* Timeouts and failures are captured per provider so a dead endpoint
  (e.g. retired GitHub Models) never aborts the whole report.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .ai_rotation import (
    _provider_base_url,
    _provider_keys,
    _resolve_meta,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderModelCatalog:
    """Result of probing one provider's ``/models`` endpoint."""

    provider: str
    http_status: int | None = None
    models: tuple[str, ...] = ()
    configured_models: tuple[str, ...] = ()
    error_type: str = ""
    error_message: str = ""
    elapsed_s: float = 0.0

    @property
    def reachable(self) -> bool:
        return self.http_status == 200

    @property
    def missing_from_remote(self) -> tuple[str, ...]:
        """Configured models the remote no longer advertises."""
        remote = set(self.models)
        return tuple(m for m in self.configured_models if m not in remote)


@dataclass
class ModelDiscoveryResult:
    """Aggregate discovery across all providers."""

    catalogs: list[ProviderModelCatalog] = field(default_factory=list)

    def by_provider(self, name: str) -> ProviderModelCatalog | None:
        for cat in self.catalogs:
            if cat.provider == name:
                return cat
        return None


async def _probe_one(
    session: aiohttp.ClientSession,
    provider: str,
    meta,
    key_name: str,
    key_value: str,
    base_url: str,
    configured_models: tuple[str, ...],
    timeout_s: float,
) -> ProviderModelCatalog:
    cat = ProviderModelCatalog(
        provider=provider,
        configured_models=configured_models,
    )
    headers = {
        "Authorization": f"Bearer {key_value}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/models"
    import time

    started = time.perf_counter()
    try:
        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
        ) as resp:
            cat.http_status = resp.status
            text = await resp.text()
            if resp.status != 200:
                cat.error_type = f"http_{resp.status}"
                cat.error_message = text[:300].replace("\n", " ")
                return cat
            try:
                import json

                data = json.loads(text)
            except json.JSONDecodeError as exc:
                cat.error_type = "response_not_json"
                cat.error_message = str(exc)
                return cat
            raw = data.get("data") if isinstance(data, dict) else None
            if not isinstance(raw, list):
                cat.error_type = "response_shape"
                cat.error_message = "expected {\"data\": [...]}"
                return cat
            ids = [str(m.get("id", "")) for m in raw if isinstance(m, dict)]
            cat.models = tuple(sorted(dict.fromkeys(m for m in ids if m)))
            return cat
    except Exception as exc:
        cat.error_type = type(exc).__name__
        cat.error_message = str(exc)[:300]
        return cat
    finally:
        cat.elapsed_s = round(time.perf_counter() - started, 3)


async def discover_models_async(
    providers: tuple[str, ...] | None = None,
    *,
    config_path=None,
    timeout_s: float = 20.0,
    concurrency: int = 4,
    load_dotenv: bool = True,
) -> ModelDiscoveryResult:
    """Query the live ``/models`` endpoint for each configured provider.

    ``providers`` defaults to the canonical :data:`PROVIDER_ORDER`.
    Providers without credentials are skipped silently.
    """
    if load_dotenv:
        from dotenv import load_dotenv as _load_dotenv

        _load_dotenv()

    from ..config import AIConfig, get_provider_metadata

    from .ai_rotation_config import PROVIDER_ORDER

    selected = list(providers) if providers else list(PROVIDER_ORDER)

    # Precompute configured model lists for cross-checking.
    ai_pool = AIConfig.from_sources(config_path=config_path)
    configured_by_name: dict[str, tuple[str, ...]] = {}
    for pool in ai_pool.providers:
        configured_by_name[pool.name] = pool.models

    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        sem = asyncio.Semaphore(concurrency)

        async def guarded(provider: str):
            meta = _resolve_meta(provider)
            if meta is None:
                return None
            keys = _provider_keys(meta)
            if not keys:
                return None
            key_name, key_value = keys[0]
            base_url = _provider_base_url(provider, meta, key_name)
            if not base_url:
                return None
            async with sem:
                return await _probe_one(
                    session,
                    provider,
                    meta,
                    key_name,
                    key_value,
                    base_url,
                    configured_by_name.get(provider, ()),
                    timeout_s,
                )

        results = await asyncio.gather(*(guarded(p) for p in selected))
    return ModelDiscoveryResult(catalogs=[r for r in results if r is not None])


def discover_models(
    providers: tuple[str, ...] | None = None,
    *,
    config_path=None,
    timeout_s: float = 20.0,
    concurrency: int = 4,
    load_dotenv: bool = True,
) -> ModelDiscoveryResult:
    """Sync wrapper around :func:`discover_models_async`."""
    return asyncio.run(
        discover_models_async(
            providers,
            config_path=config_path,
            timeout_s=timeout_s,
            concurrency=concurrency,
            load_dotenv=load_dotenv,
        )
    )


__all__ = [
    "ProviderModelCatalog",
    "ModelDiscoveryResult",
    "discover_models",
    "discover_models_async",
]
