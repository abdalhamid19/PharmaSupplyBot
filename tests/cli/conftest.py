"""Shared fixtures for CLI-level tests.

The CLI loads its config via ``load_config(config_path)`` and defaults
to ``state/config.yaml``. To exercise it from pytest without polluting
the real ``state/`` directory, every test in ``tests/cli/`` that needs
a working config can take the ``config_file`` fixture below — it
copies ``config.example.yaml`` into a tempdir and returns the path so
the test can pass ``--config <path>`` to ``run.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    """Copy ``config.example.yaml`` into ``tmp_path/state/`` and return it."""
    example = PROJECT_ROOT / "config.example.yaml"
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / "config.yaml"
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return target