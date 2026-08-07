"""Tests for Stage 3: ``ProviderMetadata`` resolution from YAML.

Covers the migration of the ``PROVIDERS`` dict from
``config_providers.py`` into the ``ai.providers.*`` YAML block.

Resolution order:
    1. ``ai.providers.{name}.{base_url,env_keys,account_id_env}`` from
       ``config.yaml``.
    2. :data:`src.core.drug_matching.config._FALLBACK_PROVIDER_METADATA`
       hardcoded fallback.
"""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from src.core.drug_matching.ai.ai_rotation import configured_attempts
from src.core.drug_matching.config import (
    AIConfig,
    PROVIDERS,
    ProviderMetadata,
    get_provider_metadata,
)


@pytest.fixture
def yaml_ai_full(tmp_path: Path) -> Path:
    """Write a temp ``config.yaml`` with both model pool + metadata."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        dedent(
            """\
            ai:
              primary_model: "test-primary"
              providers:
                groq:
                  default_model: "yaml-groq-default"
                  base_url: "https://yaml-groq.test/v1"
                  env_keys:
                    - "YAML_GROQ_KEY_1"
                    - "YAML_GROQ_KEY_2"
                  models:
                    - "yaml-groq-default"
                    - "yaml-groq-second"
                cloudflare:
                  default_model: "yaml-cf-default"
                  base_url: ""
                  env_keys:
                    - "YAML_CF_TOKEN_1"
                  account_id_env: "YAML_CF_ACCOUNT_ID"
                  models:
                    - "yaml-cf-default"
            """
        ),
        encoding="utf-8",
    )
    return cfg


# ─────────────────────────── get_provider_metadata ───────────────────────


def test_yaml_metadata_wins(yaml_ai_full: Path) -> None:
    """YAML block fields override the hardcoded fallback."""
    meta = get_provider_metadata("groq", config_path=yaml_ai_full)
    assert meta is not None
    assert meta.base_url == "https://yaml-groq.test/v1"
    assert meta.env_keys == ("YAML_GROQ_KEY_1", "YAML_GROQ_KEY_2")


def test_yaml_account_id_env_resolved(yaml_ai_full: Path) -> None:
    """Cloudflare ``account_id_env`` round-trips through YAML."""
    meta = get_provider_metadata("cloudflare", config_path=yaml_ai_full)
    assert meta is not None
    assert meta.account_id_env == "YAML_CF_ACCOUNT_ID"
    assert meta.env_keys == ("YAML_CF_TOKEN_1",)


def test_unknown_provider_returns_none(yaml_ai_full: Path) -> None:
    assert get_provider_metadata("unknownprov", config_path=yaml_ai_full) is None


def test_yaml_metadata_falls_back_when_provider_absent(tmp_path: Path) -> None:
    """A YAML with only some providers falls back to the hardcoded table for the rest."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "ai:\n  providers:\n    groq:\n      base_url: 'https://override.test'\n",
        encoding="utf-8",
    )
    meta_groq = get_provider_metadata("groq", config_path=cfg)
    assert meta_groq is not None
    assert meta_groq.base_url == "https://override.test"

    meta_cf = get_provider_metadata("cloudflare", config_path=cfg)
    assert meta_cf is not None
    assert meta_cf.account_id_env == "CLOUDFLARE_ACCOUNT_ID"  # fallback


def test_yaml_scalar_env_keys_is_split(tmp_path: Path) -> None:
    """A scalar ``env_keys: 'A,B,C'`` is split on commas."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "ai:\n  providers:\n    groq:\n      env_keys: 'A,B,C'\n",
        encoding="utf-8",
    )
    meta = get_provider_metadata("groq", config_path=cfg)
    assert meta is not None
    assert meta.env_keys == ("A", "B", "C")


def test_yaml_empty_provider_block_uses_fallback(tmp_path: Path) -> None:
    """An empty provider block does NOT crash; falls back to defaults."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("ai:\n  providers:\n    groq: {}\n", encoding="utf-8")
    meta = get_provider_metadata("groq", config_path=cfg)
    assert meta is not None
    # Falls back to fallback registry because YAML entry is empty.
    assert meta.env_keys == ("GROQ_API_KEY_1", "GROQ_API_KEY")


def test_provider_metadata_has_credentials_helper(yaml_ai_full: Path) -> None:
    """``has_credentials()`` reads from the live env (not frozen at init)."""
    meta = get_provider_metadata("groq", config_path=yaml_ai_full)
    assert meta is not None
    assert not meta.has_credentials()
    os.environ["YAML_GROQ_KEY_1"] = "test-cred"
    try:
        assert meta.has_credentials()
    finally:
        os.environ.pop("YAML_GROQ_KEY_1", None)


def test_provider_metadata_is_frozen(yaml_ai_full: Path) -> None:
    meta = get_provider_metadata("groq", config_path=yaml_ai_full)
    assert meta is not None
    with pytest.raises((AttributeError, Exception)):
        meta.base_url = "tamper"  # type: ignore[misc]


# ─────────────────────────── state/config.yaml sanity ─────────────────────


def test_state_yaml_has_all_metadata() -> None:
    """The active ``state/config.yaml`` exposes base_url + env_keys for every provider."""
    state_cfg = Path(__file__).resolve().parents[3] / "state" / "config.yaml"
    if not state_cfg.exists():
        pytest.skip("state/config.yaml not present")

    for name in [
        "groq", "opencode", "openrouter", "github", "cloudflare",
        "cerebras", "google", "mistral",
    ]:
        meta = get_provider_metadata(name)
        assert meta is not None, f"{name}: no metadata"
        # Cloudflare derives its base_url from the account_id at request
        # time, so an empty ``base_url:`` is expected.
        if name != "cloudflare":
            assert meta.base_url, f"{name}: missing base_url in state/config.yaml"
        assert meta.env_keys, f"{name}: missing env_keys in state/config.yaml"
        if name == "cloudflare":
            assert meta.account_id_env == "CLOUDFLARE_ACCOUNT_ID"


# ─────────────────────────── ai_rotation wiring ──────────────────────────


def test_configured_attempts_uses_yaml_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``configured_attempts`` reads base_url from YAML, not Python registry."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_MODELS", raising=False)

    attempts = configured_attempts("openrouter")
    assert attempts
    # The base_url matches the YAML in state/config.yaml (not Python legacy).
    assert attempts[0].base_url == "https://openrouter.ai/api/v1"


def test_configured_attempts_unknown_provider_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("UNKNOWNPROV_MODELS", raising=False)
    attempts = configured_attempts("unknownprov")
    assert attempts == ()


def test_configured_attempts_cloudflare_needs_account_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloudflare tokens without a paired ``CLOUDFLARE_ACCOUNT_ID_*`` are skipped."""
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN_1", "token-without-account")
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID_1", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_MODELS", raising=False)

    attempts = configured_attempts("cloudflare")
    assert attempts == ()


# ─────────────────────────── PROVIDERS alias ─────────────────────────────


def test_providers_dict_alias_has_all_keys() -> None:
    """The backward-compat alias still exposes the historical dict layout."""
    assert "groq" in PROVIDERS
    assert "cloudflare" in PROVIDERS
    assert "rotation" in PROVIDERS
    assert "custom" in PROVIDERS
    assert PROVIDERS["groq"]["base_url"] == "https://api.groq.com/openai/v1"
    assert PROVIDERS["cloudflare"].get("account_id_env") == "CLOUDFLARE_ACCOUNT_ID"


def test_providers_alias_opencode_base_url() -> None:
    """Health-report consumers still see the opencode base_url."""
    assert PROVIDERS["opencode"]["base_url"] == "https://opencode.ai/zen/v1"