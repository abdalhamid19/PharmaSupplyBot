"""Regression coverage for propagating the shared Excel gate scope."""

from __future__ import annotations

from types import SimpleNamespace


def test_item_worker_restores_shared_excel_gate_scope(monkeypatch):
    """A subprocess config reload must retain the parent run-key scope."""
    from src.cli.commands import item_worker

    class Config(SimpleNamespace):
        def set_excel_target_cart_gate_run_key(self, run_key):
            self.excel_target_cart_gate_run_key = str(run_key or "")

    config = Config(
        profiles={"second": object()},
        warehouse_strategy={},
        excel_target_cart_gate_run_key="",
    )
    captured = {}

    monkeypatch.setattr(item_worker, "load_config", lambda _path: config)

    def fake_build_bot(config_arg, profile_key, profile, **_options):
        captured.update(
            config=config_arg, profile_key=profile_key, profile=profile
        )
        return object()

    monkeypatch.setattr(item_worker, "build_bot", fake_build_bot)

    profile_key, _bot = item_worker._build_worker_bot(
        {
            "config_path": "state/config.yaml",
            "profile_key": "second",
            "worker_id": 0,
            "options": {
                "excel_target_cart_gate_run_key": "first/shared-run",
            },
        }
    )

    assert profile_key == "second"
    assert captured["config"] is config
    assert config.excel_target_cart_gate_run_key == "first/shared-run"


def test_worker_options_carry_shared_excel_gate_scope():
    """The parent serializes the scope into every item-worker payload."""
    from src.cli.commands.cli_order_execution import worker_options

    options = worker_options(
        SimpleNamespace(),
        app_config=SimpleNamespace(
            excel_target_cart_gate_run_key="first/shared-run"
        ),
    )

    assert options["excel_target_cart_gate_run_key"] == "first/shared-run"
