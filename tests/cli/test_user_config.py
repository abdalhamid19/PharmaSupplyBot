"""Tests for ``src.cli.cli_config`` — user config + presets loader.

These tests use ``monkeypatch`` to redirect the module-level
``GLOBAL_CONFIG_PATH`` / ``LOCAL_CONFIG_PATH`` to temp files so the
test suite never touches the real ``$HOME/.pharmabotrc`` or the
project working directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from src.cli import cli_config


# ─────────────────────────── Fixtures ────────────────────────────────


@pytest.fixture()
def isolated_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Redirect both config paths into a fresh temp directory."""
    global_path = tmp_path / "global_pharmabotrc"
    local_path = tmp_path / ".pharmabotrc"
    monkeypatch.setattr(cli_config, "GLOBAL_CONFIG_PATH", global_path)
    monkeypatch.setattr(cli_config, "LOCAL_CONFIG_PATH", local_path)
    return global_path, local_path


def _write(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


# ─────────────────────────── load_user_config ─────────────────────────


def test_load_returns_empty_when_no_files_exist(isolated_paths) -> None:
    """No files on disk → empty config, no exception."""
    cfg = cli_config.load_user_config()
    assert cfg == {"default": {}, "presets": {}}


def test_load_reads_global_only(isolated_paths) -> None:
    global_path, _ = isolated_paths
    _write(
        global_path,
        """
default:
  --profile: wardany
  --config: state/config.yaml
presets:
  quick:
    --limit: 20
    --match-only: true
""",
    )
    cfg = cli_config.load_user_config()
    assert cfg["default"] == {
        "--profile": "wardany",
        "--config": "state/config.yaml",
    }
    assert cfg["presets"] == {"quick": {"--limit": 20, "--match-only": True}}


def test_load_merges_local_over_global(isolated_paths) -> None:
    """Local config wins on conflict (per the documented precedence)."""
    global_path, local_path = isolated_paths
    _write(
        global_path,
        """
default:
  --profile: global-profile
presets:
  shared: {--limit: 10}
  global-only: {--limit: 99}
""",
    )
    _write(
        local_path,
        """
default:
  --profile: local-profile
presets:
  shared: {--limit: 50}
  local-only: {--limit: 5}
""",
    )
    cfg = cli_config.load_user_config()
    assert cfg["default"]["--profile"] == "local-profile"
    assert cfg["presets"]["shared"] == {"--limit": 50}
    assert cfg["presets"]["global-only"] == {"--limit": 99}
    assert cfg["presets"]["local-only"] == {"--limit": 5}


def test_load_tolerates_malformed_yaml(isolated_paths) -> None:
    """A broken YAML file logs a warning and returns the empty config."""
    global_path, _ = isolated_paths
    _write(global_path, ":\n  - this is: not a mapping at the top\n: invalid")
    cfg = cli_config.load_user_config()
    # Either it parsed to {} (because top-level is not a dict) or it
    # failed with YAML error → both are acceptable "ignore this file"
    # outcomes. The contract is: never raise.
    assert isinstance(cfg, dict)
    assert "default" in cfg and "presets" in cfg


def test_load_warns_on_non_mapping_top_level(isolated_paths, caplog) -> None:
    global_path, _ = isolated_paths
    _write(global_path, "- just\n- a\n- list\n")
    with caplog.at_level("WARNING", logger="src.cli.cli_config"):
        cli_config.load_user_config()
    assert any("not a YAML mapping" in rec.message for rec in caplog.records)


# ─────────────────────────── list_presets / get_preset ─────────────────


def test_list_presets_sorted(isolated_paths) -> None:
    global_path, _ = isolated_paths
    _write(
        global_path,
        """
presets:
  zeta: {}
  alpha: {}
  mu: {}
""",
    )
    assert cli_config.list_presets() == ["alpha", "mu", "zeta"]


def test_get_preset_returns_dict(isolated_paths) -> None:
    global_path, _ = isolated_paths
    _write(global_path, "presets:\n  my-preset:\n    --limit: 7\n")
    assert cli_config.get_preset("my-preset") == {"--limit": 7}


def test_get_preset_unknown_returns_empty_dict(isolated_paths) -> None:
    """Unknown presets are NOT errors here — caller decides how to handle."""
    assert cli_config.get_preset("nope") == {}


# ─────────────────────────── apply_preset ─────────────────────────────


def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default=None)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--match-only", action="store_true", default=False)
    p.add_argument("--config", default="state/config.yaml")
    return p


def test_apply_preset_fills_unset_args(isolated_paths) -> None:
    global_path, _ = isolated_paths
    _write(
        global_path,
        """
presets:
  qd:
    --limit: 20
    --match-only: true
""",
    )
    parser = _make_parser()
    args = parser.parse_args([])  # user typed nothing
    out = cli_config.apply_preset(parser, args, "qd")
    assert out.limit == 20
    assert out.match_only is True


def test_apply_preset_does_not_override_cli_args(isolated_paths) -> None:
    """User's explicit --limit wins over the preset's --limit."""
    global_path, _ = isolated_paths
    _write(
        global_path,
        "presets:\n  qd:\n    --limit: 20\n    --match-only: true\n",
    )
    parser = _make_parser()
    args = parser.parse_args(["--limit", "5"])  # user explicitly set 5
    out = cli_config.apply_preset(parser, args, "qd")
    assert out.limit == 5  # CLI wins
    assert out.match_only is True  # preset filled this one


def test_apply_preset_unknown_raises_value_error(isolated_paths) -> None:
    parser = _make_parser()
    args = parser.parse_args([])
    with pytest.raises(ValueError, match="Unknown preset 'ghost'"):
        cli_config.apply_preset(parser, args, "ghost")


def test_apply_preset_none_is_noop(isolated_paths) -> None:
    parser = _make_parser()
    args = parser.parse_args([])
    out = cli_config.apply_preset(parser, args, None)
    assert out.limit == 0 and out.match_only is False


# ─────────────────────────── inject_defaults ──────────────────────────


def test_inject_defaults_fills_unset_args(isolated_paths) -> None:
    global_path, _ = isolated_paths
    _write(
        global_path,
        """
default:
  --profile: wardany
  --config: custom.yaml
""",
    )
    parser = _make_parser()
    args = parser.parse_args([])
    out = cli_config.inject_defaults(parser, args)
    assert out.profile == "wardany"
    assert out.config == "custom.yaml"


def test_inject_defaults_respects_explicit_cli(isolated_paths) -> None:
    global_path, _ = isolated_paths
    _write(global_path, "default:\n  --profile: from-file\n")
    parser = _make_parser()
    args = parser.parse_args(["--profile", "from-cli"])
    out = cli_config.inject_defaults(parser, args)
    assert out.profile == "from-cli"  # CLI wins


def test_inject_defaults_ignores_unknown_flag(isolated_paths) -> None:
    """Flags not declared on the parser are silently skipped (no crash)."""
    global_path, _ = isolated_paths
    _write(
        global_path,
        "default:\n  --profile: wardany\n  --made-up-flag: ignored\n",
    )
    parser = _make_parser()
    args = parser.parse_args([])
    out = cli_config.inject_defaults(parser, args)
    assert out.profile == "wardany"
    assert not hasattr(out, "made_up_flag")


# ─────────────────────────── describe_sources ─────────────────────────


def test_describe_sources_reports_paths(isolated_paths) -> None:
    global_path, local_path = isolated_paths
    _write(global_path, "default:\n  --profile: g\n")
    info = cli_config.describe_sources()
    assert info["global_exists"] is True
    assert info["local_exists"] is False
    assert info["config"]["default"]["--profile"] == "g"
    assert "global_path" in info and "local_path" in info
