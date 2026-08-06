"""Configuration models for component-aware drug matching and AI review."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class AIConfig:
    """AI defaults loaded from ``ai:`` section of ``config.yaml``.

    Precedence (highest to lowest):
        1. CLI flag / explicit constructor argument
        2. Environment variable (``AI_MODEL`` / ``FALLBACK_MODELS`` /
           ``REVIEW_MODEL`` / ``AI_REVIEW_THRESHOLD`` /
           ``{PROVIDER}_MODELS``)
        3. ``ai:`` block of ``config.yaml``
        4. Hardcoded defaults in this dataclass

    The dataclass is the resolved shape — it always returns a non-empty
    value, never ``None``, so downstream consumers never have to guard
    for missing config.

    ``providers`` is a tuple of :class:`ProviderPool` entries, one per
    provider declared under ``ai.providers.*`` in YAML. Consumers that
    previously imported ``DEFAULT_MODELS`` / ``GROQ_MODELS`` from
    ``ai.ai_rotation_config`` should now call
    ``AIConfig.from_sources().provider("groq").models``.
    """

    primary_model: str = "minimax-m2.5-free"
    fallback_models: tuple[str, ...] = (
        "nemotron-3-super-free",
        "hy3-preview-free",
        "trinity-large-preview-free",
    )
    review_model: str = "big-pickle"
    review_threshold: float = 0.95
    providers: tuple["ProviderPool", ...] = ()

    @classmethod
    def from_sources(
        cls,
        *,
        primary_model: str | None = None,
        fallback_models: tuple[str, ...] | None = None,
        review_model: str | None = None,
        review_threshold: float | None = None,
        config_path: Path | None = None,
    ) -> "AIConfig":
        """Resolve AI defaults from explicit args → env → yaml → hardcoded.

        Any explicit arg that is ``None`` falls through to the next layer.
        Pass ``""`` (empty string) or ``0.0`` to skip that layer and use the
        YAML/env value verbatim — use this when the caller already loaded
        the value from a CLI flag default.
        """
        yaml_block = _load_yaml_ai_block(config_path)

        def _pick_yaml(key: str) -> Any:
            return yaml_block.get(key) if isinstance(yaml_block, dict) else None

        providers = _resolve_providers(yaml_block)

        return cls(
            primary_model=_resolve_str(
                primary_model,
                os.getenv("AI_MODEL", "").strip(),
                _pick_yaml("primary_model"),
                cls.primary_model,
            ),
            fallback_models=_resolve_tuple(
                fallback_models,
                _split_csv(os.getenv("FALLBACK_MODELS", "")),
                _pick_yaml("fallback_models"),
                cls.fallback_models,
            ),
            review_model=_resolve_str(
                review_model,
                os.getenv("REVIEW_MODEL", "").strip(),
                _pick_yaml("review_model"),
                cls.review_model,
            ),
            review_threshold=_resolve_float(
                review_threshold,
                _parse_float_env(os.getenv("AI_REVIEW_THRESHOLD", "")),
                _pick_yaml("review_threshold"),
                cls.review_threshold,
            ),
            providers=providers,
        )

    def provider(self, name: str) -> "ProviderPool | None":
        """Return the resolved :class:`ProviderPool` for ``name``, or ``None``.

        Lookup is case-insensitive (``"groq"`` and ``"GROQ"`` both match).
        """
        name_lower = name.lower()
        for pool in self.providers:
            if pool.name == name_lower:
                return pool
        return None


def _load_yaml_ai_block(config_path: Path | None) -> dict[str, Any]:
    """Best-effort load of the ``ai:`` section from ``config.yaml``.

    The path defaults to ``state/config.yaml`` (the runtime-active copy);
    falls back to ``config.yaml`` then ``config.example.yaml`` if the
    active file is missing. Malformed YAML is logged and ignored — the
    dataclass hardcoded defaults take over.
    """
    candidates: list[Path] = []
    if config_path is not None:
        candidates.append(config_path)
    candidates.append(ROOT_DIR / "state" / "config.yaml")
    candidates.append(ROOT_DIR / "config.yaml")
    candidates.append(ROOT_DIR / "config.example.yaml")

    for path in candidates:
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(
                "could not read AI config from %s: %s "
                "(falling back to hardcoded defaults)",
                path,
                exc,
            )
            return {}
        if not isinstance(data, dict):
            return {}
        block = data.get("ai")
        if isinstance(block, dict):
            return block
        return {}
    return {}


def _split_csv(raw: str) -> tuple[str, ...]:
    return tuple(piece.strip() for piece in raw.split(",") if piece.strip())


def _parse_float_env(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "ignoring non-numeric AI_REVIEW_THRESHOLD env value: %r", raw
        )
        return None


def _resolve_str(*layers: Any) -> str:
    """Pick the first non-empty layer (string-level precedence)."""
    default = layers[-1] if layers else ""
    for layer in layers[:-1]:
        if isinstance(layer, str) and layer.strip():
            return layer.strip()
    return default if isinstance(default, str) else str(default)


def _resolve_tuple(*layers: Any) -> tuple[str, ...]:
    """Pick the first non-empty layer (tuple-level precedence).

    Accepts tuples, lists, scalars (str), and comma-separated strings —
    scalar inputs are coerced to a single-element tuple; CSV strings are
    split on commas. Whitespace-only pieces are dropped.
    """
    default = layers[-1] if layers else ()
    for layer in layers[:-1]:
        if isinstance(layer, (tuple, list)):
            cleaned = tuple(
                str(piece).strip() for piece in layer if str(piece).strip()
            )
            if cleaned:
                return cleaned
        elif isinstance(layer, str):
            cleaned = tuple(
                piece.strip() for piece in layer.split(",") if piece.strip()
            )
            if cleaned:
                return cleaned
    if isinstance(default, (tuple, list)):
        return tuple(default)
    return ()


def _resolve_float(*layers: Any) -> float:
    """Pick the first non-None numeric layer."""
    default = layers[-1] if layers else 0.0
    for layer in layers[:-1]:
        if layer is None:
            continue
        if isinstance(layer, bool):
            # bool is a subclass of int — exclude to avoid True-as-1.0 bugs.
            continue
        if isinstance(layer, (int, float)):
            return float(layer)
    try:
        return float(default)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class ProviderPool:
    """Resolved per-provider model list.

    Replaces the previous hardcoded ``GROQ_MODELS`` / ``OPENROUTER_MODELS``
    / ``DEFAULT_MODELS`` constants in
    :mod:`src.core.drug_matching.ai.ai_rotation_config`.

    The ``default_model`` is the first entry of ``models`` (or an explicit
    ``default_model:`` from YAML), used by
    :func:`src.core.drug_matching.config.config_helpers.resolve_api_config`
    when no ``--model`` flag / env override is set for that provider.

    The ``models`` list is used by ``ai.ai_rotation._provider_models``
    to enumerate rotation attempts.
    """

    name: str
    default_model: str
    models: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.default_model and self.models:
            object.__setattr__(self, "default_model", self.models[0])


def _resolve_providers(yaml_block: dict[str, Any]) -> tuple[ProviderPool, ...]:
    """Build a sorted tuple of :class:`ProviderPool` from a YAML ``ai:`` block.

    Resolution per provider:
        1. ``{PROVIDER}_MODELS`` env var (CSV) — wins if non-empty.
        2. ``ai.providers.{name}.models`` from YAML.
        3. Skip the provider entirely (returns an empty tuple) if neither
           yields a non-empty list — the consumer can then fall back to
           the ``PROVIDERS[provider].default_model`` from
           :mod:`config_providers` if available.

    Returns a tuple (not a dict) so the dataclass stays hashable and
    immutable. Use :meth:`AIConfig.provider` for by-name lookups.
    """
    raw_providers = (
        yaml_block.get("providers") if isinstance(yaml_block, dict) else None
    )
    if not isinstance(raw_providers, dict):
        return ()

    pools: list[ProviderPool] = []
    for name in sorted(raw_providers):
        block = raw_providers.get(name)
        if not isinstance(block, dict):
            continue

        env_name = f"{name.upper()}_MODELS"
        env_models = _split_csv(os.getenv(env_name, ""))
        yaml_models = block.get("models")
        yaml_default = block.get("default_model")

        # Layer 1 (env) wins over Layer 2 (yaml).
        if env_models:
            models = env_models
        elif isinstance(yaml_models, list):
            models = tuple(
                str(m).strip() for m in yaml_models if str(m).strip()
            )
        elif isinstance(yaml_models, str):
            models = _split_csv(yaml_models)
        else:
            continue  # no models defined for this provider

        if not models:
            continue

        default_model = (
            str(yaml_default).strip()
            if isinstance(yaml_default, str) and yaml_default.strip()
            else models[0]
        )

        pools.append(
            ProviderPool(
                name=name,
                default_model=default_model,
                models=models,
            )
        )
    return tuple(pools)


# ─────────────────────────── ProviderMetadata ───────────────────────────


@dataclass(frozen=True)
class ProviderMetadata:
    """Resolved per-provider connection settings.

    Replaces the previous hardcoded ``PROVIDERS`` dict in
    :mod:`src.core.drug_matching.config.config_providers`. Carries the
    bits that are NOT model lists: the API base URL, the env-var names
    that hold credentials (multiple for rotation), and any per-provider
    account-id env var (currently only Cloudflare).

    Combined with :class:`ProviderPool` (same ``name``), the two cover
    everything the rotation layer needs without touching
    ``config_providers.py`` anymore.
    """

    name: str
    base_url: str = ""
    env_keys: tuple[str, ...] = ()
    account_id_env: str = ""

    def has_credentials(self) -> bool:
        """Return True when at least one env_key resolves to a non-empty value."""
        return any(os.getenv(k, "").strip() for k in self.env_keys)


#: Fallback metadata for the 8 supported providers, used when the
#: active ``config.yaml`` does not declare ``ai.providers.<name>.*``.
#: This keeps the runtime working in environments that have not yet
#: migrated (e.g. legacy ``state/config.yaml`` without ``base_url:``).
_FALLBACK_PROVIDER_METADATA: dict[str, ProviderMetadata] = {
    "openrouter": ProviderMetadata(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        env_keys=("OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY"),
    ),
    "opencode": ProviderMetadata(
        name="opencode",
        base_url="https://opencode.ai/zen/v1",
        env_keys=("OPENCODE_API_KEY_1", "OPENCODE_API_KEY"),
    ),
    "groq": ProviderMetadata(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        env_keys=("GROQ_API_KEY_1", "GROQ_API_KEY"),
    ),
    "github": ProviderMetadata(
        name="github",
        base_url="https://models.github.ai/inference",
        env_keys=("GITHUB_API_KEY_1", "GITHUB_API_KEY"),
    ),
    "cloudflare": ProviderMetadata(
        name="cloudflare",
        base_url="",
        env_keys=("CLOUDFLARE_API_TOKEN_1", "CLOUDFLARE_API_TOKEN"),
        account_id_env="CLOUDFLARE_ACCOUNT_ID",
    ),
    "cerebras": ProviderMetadata(
        name="cerebras",
        base_url="https://api.cerebras.ai/v1",
        env_keys=("CEREBRAS_API_KEY_1", "CEREBRAS_API_KEY"),
    ),
    "google": ProviderMetadata(
        name="google",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        env_keys=("GOOGLE_API_KEY_1", "GOOGLE_API_KEY"),
    ),
    "mistral": ProviderMetadata(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        env_keys=("MISTRAL_API_KEY_1", "MISTRAL_API_KEY"),
    ),
    "custom": ProviderMetadata(
        name="custom",
        env_keys=("CUSTOM_API_KEY",),
    ),
}


def _yaml_block_has_metadata(block: dict[str, Any]) -> bool:
    """Return True if a YAML provider block declares any connection field.

    Used by :func:`get_provider_metadata` to decide between honouring
    the YAML entry (even if partially filled) and falling back to the
    hardcoded table. Empty blocks (``ai.providers.groq: {}``) are
    treated as 'no YAML metadata here'.
    """
    return any(
        key in block
        for key in ("base_url", "env_keys", "env_key", "account_id_env")
    )


def get_provider_metadata(
    name: str,
    *,
    config_path: Path | None = None,
) -> ProviderMetadata | None:
    """Resolve :class:`ProviderMetadata` for ``name``.

    Resolution order:
        1. ``ai.providers.{name}`` block in ``config.yaml`` — only if
           it declares at least one connection field (``base_url`` /
           ``env_keys`` / ``env_key`` / ``account_id_env``). An empty
           block (``ai.providers.<name>: {}``) is treated as 'not
           declared here' so the hardcoded fallback takes over.
        2. :data:`_FALLBACK_PROVIDER_METADATA` (hardcoded registry).

    Returns ``None`` when the provider is unknown on both layers. The
    ``rotation`` pseudo-provider is intentionally absent from the
    fallback table — callers must handle it explicitly via
    :func:`PROVIDER_ORDER` from ``ai_rotation_config``.
    """
    yaml_block = _load_yaml_ai_block(config_path)
    raw_providers = (
        yaml_block.get("providers") if isinstance(yaml_block, dict) else None
    )
    if isinstance(raw_providers, dict):
        block = raw_providers.get(name)
        if isinstance(block, dict) and _yaml_block_has_metadata(block):
            base_url = str(block.get("base_url", "")).strip()
            raw_keys = block.get("env_keys")
            if isinstance(raw_keys, list):
                env_keys = tuple(
                    str(k).strip() for k in raw_keys if str(k).strip()
                )
            elif isinstance(raw_keys, str):
                env_keys = tuple(
                    k.strip() for k in raw_keys.split(",") if k.strip()
                )
            elif isinstance(block.get("env_key"), str):
                # Legacy single-key layout — accept for back-compat.
                env_keys = (block["env_key"].strip(),)
            else:
                env_keys = ()
            account_id_env = str(block.get("account_id_env", "")).strip()
            return ProviderMetadata(
                name=name,
                base_url=base_url,
                env_keys=env_keys,
                account_id_env=account_id_env,
            )

    return _FALLBACK_PROVIDER_METADATA.get(name)


@dataclass(frozen=True)
class MatchingConfig:
    """Thresholds used by the indexed drug matcher."""

    fuzzy_threshold: int = 80
    brand_prefix_min: int = 4
    brand_prefix_ratio: float = 0.75
    fuzzy_prefix_len: int = 3
    early_stop_confidence: float = 0.95
    candidate_top_k: int = 5
    query_cache_size: int = 256
    ai_verify_threshold: float = 90.0
    ai_batch_size: int = 20
    ai_max_concurrent: int = 5
    top_k_candidates: int = 10
    ai_review_threshold: float = 0.8
    ai_search_limit: int | None = None
    ai_verify_policy: str = "score"
    ai_verify_limit: int | None = None
    ai_search_policy: str = "review-candidates"
    ai_search_min_candidate_score: float = 80.0
    ai_search_accept_confidence: float = 0.75
    ai_search_candidate_limit: int = 5
    ai_search_review_candidate_min_score: float = 68.0
    ai_search_review_candidate_limit: int = 8
    ai_search_review_accept_confidence: float = 0.85
    ai_search_allow_component_mismatch_reasons: tuple[str, ...] = (
        "different_brand",
        "brand_prefix_mismatch",
        "different_import_status",
        "different_modifier",
        "different_quantity",
        "different_volume",
    )


@dataclass(frozen=True)
class APIConfig:
    """AI API settings for verification, search, and model rotation."""

    api_key: str = ""
    api_keys: tuple[str, ...] = ()
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-4o-mini"
    fallback_models: tuple[str, ...] = ()
    review_model: str = ""
    healthy_combos: tuple = ()
    attempt_plan: tuple = ()
    review_attempt_plan: tuple = ()
    max_tokens: int = 1024
    temperature: float = 0.1


@dataclass(frozen=True)
class Paths:
    """Default CSV paths for standalone product matching."""

    drugs_csv: Path = field(default_factory=lambda: ROOT_DIR / "data/input/order_items")
    tawreed_csv: Path = field(
        default_factory=lambda: ROOT_DIR / "artifacts/wardany/tawreed_products.csv"
    )
    output_csv: Path = field(default_factory=lambda: _default_output_csv())
    env_file: Path = field(default_factory=lambda: ROOT_DIR / ".env")


def _default_output_csv() -> Path:
    stem = datetime.now().strftime("matched_drugs_verified_%Y%m%d_%H%M%S.csv")
    return ROOT_DIR / "artifacts" / "matching" / stem


__all__ = [
    "ROOT_DIR",
    "MatchingConfig",
    "APIConfig",
    "AIConfig",
    "ProviderPool",
    "ProviderMetadata",
    "get_provider_metadata",
    "Paths",
    "_default_output_csv",
]
