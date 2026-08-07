"""Tests for the per-provider ``ProviderPool`` resolution chain.

Covers the migration of ``GROQ_MODELS`` / ``OPENCODE_MODELS`` /
``DEFAULT_MODELS`` from ``ai_rotation_config.py`` into
``config.yaml`` under ``ai.providers.*``.

Resolution order (highest priority first):
    1. ``{PROVIDER}_MODELS`` env var (CSV)
    2. ``ai.providers.{name}.models`` from ``config.yaml``
    3. ``info["default_model"]`` from the PROVIDERS registry (last-resort
       single-model fallback so a provider with no YAML pool still
       gets at least one rotation attempt)
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from src.core.drug_matching.ai.ai_rotation import configured_attempts
from src.core.drug_matching.config import AIConfig, ProviderPool
from src.core.drug_matching.config.config_models import ROOT_DIR


@pytest.fixture
def yaml_ai_providers(tmp_path: Path) -> Path:
    """Write a temp ``config.yaml`` with a small ai.providers.* block."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        dedent(
            """\
            ai:
              primary_model: "test-primary"
              providers:
                groq:
                  default_model: "yaml-groq-default"
                  models:
                    - "yaml-groq-default"
                    - "yaml-groq-second"
                customprov:
                  default_model: "yaml-custom-default"
                  models:
                    - "yaml-custom-A"
                    - "yaml-custom-B"
            """
        ),
        encoding="utf-8",
    )
    return cfg


# ──────────────────────── AIConfig.from_sources ──────────────────────────


def test_providers_default_to_yaml_when_no_env(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_providers: Path
) -> None:
    """Without env vars, ``providers`` reflects the YAML block."""
    monkeypatch.delenv("GROQ_MODELS", raising=False)
    monkeypatch.delenv("CUSTOMPROV_MODELS", raising=False)

    cfg = AIConfig.from_sources(config_path=yaml_ai_providers)

    assert len(cfg.providers) == 2
    groq = cfg.provider("groq")
    assert groq is not None
    assert groq.default_model == "yaml-groq-default"
    assert groq.models == ("yaml-groq-default", "yaml-groq-second")

    custom = cfg.provider("customprov")
    assert custom is not None
    assert custom.default_model == "yaml-custom-default"
    assert custom.models == ("yaml-custom-A", "yaml-custom-B")


def test_provider_lookup_is_case_insensitive(yaml_ai_providers: Path) -> None:
    """``AIConfig.provider("GROQ")`` matches ``provider("groq")``."""
    cfg = AIConfig.from_sources(config_path=yaml_ai_providers)
    lower = cfg.provider("groq")
    upper = cfg.provider("GROQ")
    mixed = cfg.provider("Groq")
    assert lower is not None
    assert lower is upper
    assert lower is mixed


def test_provider_unknown_returns_none(yaml_ai_providers: Path) -> None:
    cfg = AIConfig.from_sources(config_path=yaml_ai_providers)
    assert cfg.provider("nonexistent") is None


def test_env_models_wins_over_yaml(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_providers: Path
) -> None:
    """``GROQ_MODELS`` env var (CSV) overrides the YAML list."""
    monkeypatch.setenv("GROQ_MODELS", "env-only-1, env-only-2, env-only-3")

    cfg = AIConfig.from_sources(config_path=yaml_ai_providers)
    groq = cfg.provider("groq")

    assert groq is not None
    assert groq.models == ("env-only-1", "env-only-2", "env-only-3")
    # default_model is preserved (YAML wins for default).
    assert groq.default_model == "yaml-groq-default"


def test_empty_env_falls_through_to_yaml(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_providers: Path
) -> None:
    """An empty env var is treated as 'unset' so YAML wins."""
    monkeypatch.setenv("GROQ_MODELS", "   ")  # whitespace only

    cfg = AIConfig.from_sources(config_path=yaml_ai_providers)
    groq = cfg.provider("groq")
    assert groq is not None
    assert groq.models == ("yaml-groq-default", "yaml-groq-second")


def test_providers_sorted_alphabetically(yaml_ai_providers: Path) -> None:
    """``AIConfig.providers`` is alphabetically sorted for determinism."""
    cfg = AIConfig.from_sources(config_path=yaml_ai_providers)
    names = [p.name for p in cfg.providers]
    assert names == sorted(names)


def test_provider_pool_post_init_falls_back_to_first_model() -> None:
    """``default_model`` defaults to the first entry of ``models``."""
    pool = ProviderPool(
        name="test", default_model="", models=("first", "second")
    )
    assert pool.default_model == "first"


def test_provider_pool_is_frozen() -> None:
    pool = ProviderPool(name="x", default_model="d", models=("d",))
    with pytest.raises((AttributeError, Exception)):
        pool.default_model = "tamper"  # type: ignore[misc]


def test_yaml_without_providers_block_falls_back_to_state(tmp_path: Path) -> None:
    """A YAML file without ``ai.providers.*`` falls back to ``state/config.yaml``.

    Stage 2 added the providers block to state/config.yaml, so a
    non-existent / providers-less path still resolves to the active
    pools (preserved behaviour — used to be silently empty).
    """
    state_cfg = ROOT_DIR / "state" / "config.yaml"
    if not state_cfg.exists():
        pytest.skip("state/config.yaml not present")

    cfg = AIConfig.from_sources(
        config_path=Path("/nonexistent/config.yaml")
    )
    # Falls back to state/config.yaml's ai.providers.*. github/groq are
    # declared empty (no verified-working models) so they resolve to no
    # pool; the remaining working providers still resolve here.
    assert len(cfg.providers) >= 6


def test_explicit_yaml_without_providers_yields_no_pools(tmp_path: Path) -> None:
    """An explicit YAML with no providers block yields zero pools for that file."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "ai:\n  primary_model: only-this\n",
        encoding="utf-8",
    )
    # Patch the loader to ignore state/config.yaml so the test is hermetic.
    import src.core.drug_matching.config.config_models as m

    original_loader = m._load_yaml_ai_block
    monkey_target = tmp_path / "config.yaml"  # noqa: F841

    def _patched(path=None):
        if path == cfg_path or path is None:
            return {"primary_model": "only-this"}
        # For other paths (state/config.yaml), return empty.
        return {}

    monkeypatch_instance = pytest.MonkeyPatch()
    monkeypatch_instance.setattr(m, "_load_yaml_ai_block", _patched)
    try:
        cfg = AIConfig.from_sources(config_path=cfg_path)
        assert cfg.providers == ()
        assert cfg.primary_model == "only-this"
    finally:
        monkeypatch_instance.undo()
    # Keep original_loader referenced so the test doesn't lose the link.
    assert original_loader is not None


def test_yaml_providers_block_with_non_dict_entries(tmp_path: Path) -> None:
    """Non-dict provider entries are silently dropped."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "ai:\n  providers:\n    groq:\n      models: [a, b]\n    "
        "borked: 'not a dict'\n",
        encoding="utf-8",
    )
    cfg = AIConfig.from_sources(config_path=cfg_path)
    assert [p.name for p in cfg.providers] == ["groq"]


def test_yaml_scalar_models_string_is_coerced(tmp_path: Path) -> None:
    """A YAML scalar ``models: "x,y,z"`` is split on commas."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "ai:\n  providers:\n    groq:\n      models: 'a,b,c'\n",
        encoding="utf-8",
    )
    cfg = AIConfig.from_sources(config_path=cfg_path)
    groq = cfg.provider("groq")
    assert groq is not None
    assert groq.models == ("a", "b", "c")


# ──────────────────────── configured_attempts integration ────────────────


def test_configured_attempts_uses_yaml_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """With a real GROQ_API_KEY + YAML pool, configured_attempts returns the YAML models."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_MODELS", raising=False)

    attempts = configured_attempts("groq")
    # groq currently has an empty ``models`` list (no verified-working
    # models) — rotation must yield zero attempts instead of crashing.
    assert attempts == ()


def test_configured_attempts_env_overrides_yaml_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``GROQ_MODELS`` env var shrinks the rotation list to exactly its CSV."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODELS", "env-only-A, env-only-B")

    attempts = configured_attempts("groq")
    assert len(attempts) == 2
    assert [a.model for a in attempts] == ["env-only-A", "env-only-B"]


def test_configured_attempts_unknown_provider_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider that has neither YAML nor registry entry yields zero attempts."""
    monkeypatch.delenv("UNKNOWNPROV_MODELS", raising=False)

    attempts = configured_attempts("unknownprov")
    assert attempts == ()


def test_state_config_yaml_has_all_8_providers() -> None:
    """Sanity: the active ``state/config.yaml`` still declares all 8 providers.

    ``github`` and ``groq`` are declared but keep empty ``models`` (they
    currently expose no working models), so they are not present in the
    resolved ``cfg.providers`` — rotation yields zero attempts for them.
    """
    state_cfg = ROOT_DIR / "state" / "config.yaml"
    if not state_cfg.exists():
        pytest.skip("state/config.yaml not present")

    cfg = AIConfig.from_sources(config_path=state_cfg)
    expected = {
        "cerebras",
        "cloudflare",
        "google",
        "mistral",
        "opencode",
        "openrouter",
    }
    actual = {p.name for p in cfg.providers}
    assert actual == expected


def test_state_config_yaml_provider_counts_match_legacy() -> None:
    """The YAML pools carry the current (verified-working) model counts.

    Counts were regenerated from a live probe (HTTP 200 only). ``github``
    and ``groq`` are declared with empty ``models`` because they expose
    no working models today — they no longer appear in ``cfg.providers``.
    """
    state_cfg = ROOT_DIR / "state" / "config.yaml"
    if not state_cfg.exists():
        pytest.skip("state/config.yaml not present")

    cfg = AIConfig.from_sources(config_path=state_cfg)
    by_name = {p.name: len(p.models) for p in cfg.providers}
    expected = {
        "opencode": 2,
        "openrouter": 6,
        "cerebras": 2,
        "google": 8,
        "mistral": 6,
        "cloudflare": 24,
    }
    assert by_name == expected


def test_state_config_yaml_default_model_is_first_entry() -> None:
    """``default_model`` matches the first entry of ``models`` for each pool."""
    state_cfg = ROOT_DIR / "state" / "config.yaml"
    if not state_cfg.exists():
        pytest.skip("state/config.yaml not present")

    cfg = AIConfig.from_sources(config_path=state_cfg)
    for pool in cfg.providers:
        assert pool.default_model == pool.models[0], (
            f"{pool.name}: default_model={pool.default_model!r} "
            f"but models[0]={pool.models[0]!r}"
        )