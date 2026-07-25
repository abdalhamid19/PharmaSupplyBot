"""Tests for :class:`AIConfig` precedence resolution.

Covers the four-layer precedence chain introduced in Stage 1 of the
``config.yaml`` migration:

    CLI/explicit arg > env var > ``ai:`` block in ``config.yaml`` > hardcoded default

These tests use temporary YAML files and ``monkeypatch`` to isolate
each layer from the others, so the project's actual ``state/config.yaml``
and ``.env`` cannot leak into the assertions.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest

from src.core.drug_matching.config import AIConfig
from src.core.drug_matching.config.config_helpers import (
    _fallback_models,
    resolve_api_config,
)
from src.core.drug_matching.config.config_models import ROOT_DIR


# ──────────────────────── AIConfig.from_sources ──────────────────────────


@pytest.fixture
def yaml_ai_block(tmp_path: Path) -> Path:
    """Write a temporary ``config.yaml`` with an ``ai:`` block."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        dedent(
            """\
            site:
              base_url: "https://example.test/"
            ai:
              primary_model: "yaml-primary"
              fallback_models:
                - "yaml-fb-1"
                - "yaml-fb-2"
              review_model: "yaml-review"
              review_threshold: 0.88
            """
        ),
        encoding="utf-8",
    )
    return config_path


def test_from_sources_uses_hardcoded_when_no_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env, no YAML → dataclass defaults are returned."""
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("FALLBACK_MODELS", raising=False)
    monkeypatch.delenv("REVIEW_MODEL", raising=False)
    monkeypatch.delenv("AI_REVIEW_THRESHOLD", raising=False)

    cfg = AIConfig.from_sources(config_path=Path("/nonexistent/config.yaml"))

    assert cfg.primary_model == "minimax-m2.5-free"
    assert cfg.fallback_models == (
        "nemotron-3-super-free",
        "hy3-preview-free",
        "trinity-large-preview-free",
    )
    assert cfg.review_model == "big-pickle"
    assert cfg.review_threshold == pytest.approx(0.95)


def test_from_sources_yaml_layer_overrides_defaults(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    """``ai:`` YAML block wins over the hardcoded defaults."""
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("FALLBACK_MODELS", raising=False)
    monkeypatch.delenv("REVIEW_MODEL", raising=False)
    monkeypatch.delenv("AI_REVIEW_THRESHOLD", raising=False)

    cfg = AIConfig.from_sources(config_path=yaml_ai_block)

    assert cfg.primary_model == "yaml-primary"
    assert cfg.fallback_models == ("yaml-fb-1", "yaml-fb-2")
    assert cfg.review_model == "yaml-review"
    assert cfg.review_threshold == pytest.approx(0.88)


def test_from_sources_env_layer_overrides_yaml(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    """Env vars win over the YAML block."""
    monkeypatch.setenv("AI_MODEL", "env-primary")
    monkeypatch.setenv("FALLBACK_MODELS", "env-fb-1, env-fb-2, env-fb-3")
    monkeypatch.setenv("REVIEW_MODEL", "env-review")
    monkeypatch.setenv("AI_REVIEW_THRESHOLD", "0.77")

    cfg = AIConfig.from_sources(config_path=yaml_ai_block)

    assert cfg.primary_model == "env-primary"
    assert cfg.fallback_models == ("env-fb-1", "env-fb-2", "env-fb-3")
    assert cfg.review_model == "env-review"
    assert cfg.review_threshold == pytest.approx(0.77)


def test_from_sources_explicit_args_override_env(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    """Explicit kwargs are the highest-precedence layer."""
    monkeypatch.setenv("AI_MODEL", "env-primary")
    monkeypatch.setenv("FALLBACK_MODELS", "env-fb-1")
    monkeypatch.setenv("REVIEW_MODEL", "env-review")
    monkeypatch.setenv("AI_REVIEW_THRESHOLD", "0.5")

    cfg = AIConfig.from_sources(
        primary_model="arg-primary",
        fallback_models=("arg-fb-1", "arg-fb-2"),
        review_model="arg-review",
        review_threshold=0.42,
        config_path=yaml_ai_block,
    )

    assert cfg.primary_model == "arg-primary"
    assert cfg.fallback_models == ("arg-fb-1", "arg-fb-2")
    assert cfg.review_model == "arg-review"
    assert cfg.review_threshold == pytest.approx(0.42)


def test_from_sources_partial_explicit_args_fall_through(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    """Only ``None`` explicit args fall through; provided ones stay."""
    monkeypatch.setenv("AI_MODEL", "env-primary")
    monkeypatch.delenv("REVIEW_MODEL", raising=False)

    cfg = AIConfig.from_sources(
        primary_model=None,  # fall through
        review_model="arg-review",  # explicit
        config_path=yaml_ai_block,
    )

    assert cfg.primary_model == "env-primary"  # env > yaml
    assert cfg.review_model == "arg-review"  # explicit wins


def test_from_sources_empty_env_uses_yaml_layer(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    """An empty env var is treated as 'unset' so YAML takes over."""
    monkeypatch.setenv("AI_MODEL", "")
    monkeypatch.setenv("REVIEW_MODEL", "   ")  # whitespace-only

    cfg = AIConfig.from_sources(config_path=yaml_ai_block)

    assert cfg.primary_model == "yaml-primary"
    assert cfg.review_model == "yaml-review"


def test_from_sources_invalid_float_env_falls_back(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    """Non-numeric ``AI_REVIEW_THRESHOLD`` is logged and ignored."""
    monkeypatch.setenv("AI_REVIEW_THRESHOLD", "not-a-number")

    cfg = AIConfig.from_sources(config_path=yaml_ai_block)

    assert cfg.review_threshold == pytest.approx(0.88)  # YAML value


def test_from_sources_malformed_yaml_uses_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Garbage YAML must not crash the resolver."""
    bad_yaml = tmp_path / "config.yaml"
    bad_yaml.write_text("ai: : : invalid\n  - ]\n", encoding="utf-8")
    monkeypatch.delenv("AI_MODEL", raising=False)

    cfg = AIConfig.from_sources(config_path=bad_yaml)

    # Falls all the way through to dataclass defaults.
    assert cfg.primary_model == "minimax-m2.5-free"


def test_from_sources_missing_yaml_searches_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without an explicit config_path, ROOT_DIR/state/config.yaml is consulted."""
    monkeypatch.delenv("AI_MODEL", raising=False)
    state_cfg = ROOT_DIR / "state" / "config.yaml"
    if not state_cfg.exists():
        pytest.skip("state/config.yaml not present in this checkout")

    cfg = AIConfig.from_sources()
    # Real values from state/config.yaml in this repo.
    assert cfg.primary_model == "minimax-m2.5-free"
    assert cfg.review_model == "big-pickle"
    assert cfg.fallback_models == (
        "nemotron-3-super-free",
        "hy3-preview-free",
        "trinity-large-preview-free",
    )


def test_ai_config_is_frozen() -> None:
    """``AIConfig`` is a frozen dataclass — mutation must raise."""
    cfg = AIConfig.from_sources()
    with pytest.raises((AttributeError, Exception)):
        cfg.primary_model = "tampered"  # type: ignore[misc]


# ──────────────────────── _fallback_models helper ────────────────────────


def test_fallback_models_prefers_env(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    monkeypatch.setenv("FALLBACK_MODELS", "env-only-1, env-only-2")

    assert _fallback_models() == ("env-only-1", "env-only-2")


def test_fallback_models_yaml_when_env_unset(
    monkeypatch: pytest.MonkeyPatch, yaml_ai_block: Path
) -> None:
    monkeypatch.delenv("FALLBACK_MODELS", raising=False)

    # Patch the loader so it returns our YAML block instead of the
    # repo's state/config.yaml — we want a deterministic value here.
    import src.core.drug_matching.config.config_models as m

    monkeypatch.setattr(
        m, "_load_yaml_ai_block", lambda config_path=None: {
            "fallback_models": ["yaml-fb-1", "yaml-fb-2"],
        }
    )

    assert _fallback_models() == ("yaml-fb-1", "yaml-fb-2")


def test_fallback_models_hardcoded_when_all_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FALLBACK_MODELS", raising=False)

    # Force the YAML loader to return nothing.
    import src.core.drug_matching.config.config_models as m

    monkeypatch.setattr(m, "_load_yaml_ai_block", lambda config_path=None: {})

    assert _fallback_models() == (
        "nemotron-3-super-free",
        "hy3-preview-free",
        "trinity-large-preview-free",
    )


# ──────────────────────── resolve_api_config integration ─────────────────


def test_resolve_api_config_uses_yaml_when_no_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_api_config(model="") now reads from AIConfig (YAML)."""
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("FALLBACK_MODELS", raising=False)

    import src.core.drug_matching.config.config_models as m

    monkeypatch.setattr(
        m, "_load_yaml_ai_block", lambda config_path=None: {
            "primary_model": "yaml-primary",
            "fallback_models": ["yaml-fb"],
        }
    )

    resolved = resolve_api_config()

    assert resolved["model"] == "yaml-primary"
    assert resolved["fallback_models"] == ("yaml-fb",)


def test_resolve_api_config_explicit_model_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit ``model=`` argument short-circuits env + YAML."""
    monkeypatch.setenv("AI_MODEL", "env-primary")

    resolved = resolve_api_config(model="explicit-model")

    assert resolved["model"] == "explicit-model"


def test_resolve_api_config_provider_path_uses_yaml_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider-specific path also benefits from the AIConfig fallback."""
    monkeypatch.delenv("AI_MODEL", raising=False)

    import src.core.drug_matching.config.config_models as m

    monkeypatch.setattr(
        m, "_load_yaml_ai_block", lambda config_path=None: {
            "primary_model": "yaml-primary",
        }
    )

    resolved = resolve_api_config(provider="groq", model="", api_key="")

    assert resolved["model"] == "yaml-primary"


# ──────────────────────── YAML fallback chain ────────────────────────────


def test_yaml_loader_skips_when_ai_block_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A YAML file without an ``ai:`` block returns ``{}`` — no crash."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        dedent(
            """\
            site:
              base_url: "https://example.test/"
            runtime:
              headless: true
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("AI_MODEL", raising=False)

    cfg = AIConfig.from_sources(config_path=cfg_path)

    # Falls through to dataclass defaults.
    assert cfg.primary_model == "minimax-m2.5-free"


def test_yaml_loader_handles_scalar_fallback_models(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A YAML scalar for ``fallback_models`` is coerced to a 1-tuple."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "ai:\n  fallback_models: single-model\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FALLBACK_MODELS", raising=False)

    cfg = AIConfig.from_sources(config_path=cfg_path)

    assert cfg.fallback_models == ("single-model",)