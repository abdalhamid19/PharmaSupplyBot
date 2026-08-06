"""Behavioural tests for the Typer CLI surface.

These tests replace the legacy ``parser.parse_args(...)`` style tests in
``tests/cli/parsers/test_cli_parser.py``. Instead of asserting on the
argparse ``Namespace`` directly, they verify that:

* the Typer app accepts each flag without error,
* the flag value is forwarded to the registered handler, and
* the resulting ``--help`` output documents the flag.

The handlers themselves are mocked so we never touch Playwright, the
Tawreed API, or any other external system. What we are testing is the
*shape of the contract between the Typer parser and the registry*.
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from src.cli.typer_app import app


# ─────────────────────────── auth ───────────────────────────


def _invoke(argv: list[str], captured: dict, **patches) -> object:
    """Helper: invoke the app with ``argv``, capture the handler's args."""
    runner = CliRunner()
    with patch("src.cli.typer_app.get_command") as get_cmd, \
         patch("src.cli.typer_app.load_config") as load_cfg, \
         patch("src.cli.typer_app.configure_logging"):

        def fake_handler(cfg, args):
            for k in captured:
                captured[k] = getattr(args, k, None)
            return 0

        get_cmd.return_value = fake_handler
        load_cfg.return_value = object()
        return runner.invoke(app, argv)


def test_auth_accepts_headless_flag() -> None:
    captured: dict = {"headless": None}
    result = _invoke(["auth", "--profile", "wardany", "--headless"], captured)
    assert result.exit_code == 0
    assert captured["headless"] is True


def test_auth_help_lists_headless_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "--headless" in result.stdout


def test_auth_does_not_expose_debug_browser_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "--debug-browser" not in result.stdout


# ─────────────────────────── order ───────────────────────────


def test_order_accepts_debug_browser_flag() -> None:
    captured: dict = {"debug_browser": None, "cmd": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--debug-browser",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["debug_browser"] is True
    assert captured["cmd"] == "order"


def test_order_accepts_warehouse_mode_override() -> None:
    captured: dict = {"warehouse_mode": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--warehouse-mode", "max_discount",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["warehouse_mode"] == "max_discount"


def test_order_accepts_min_discount_override() -> None:
    captured: dict = {"min_discount_percent": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--min-discount-percent", "12",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["min_discount_percent"] == 12.0


def test_order_accepts_resume_and_stop_flag() -> None:
    captured: dict = {"resume": None, "stop_flag": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--resume",
            "--stop-flag", "artifacts/run_control/order_stop.flag",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["resume"] is True
    assert captured["stop_flag"] == "artifacts/run_control/order_stop.flag"


def test_order_accepts_fast_search_flag() -> None:
    captured: dict = {"fast_search": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--fast-search",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["fast_search"] is True


def test_order_accepts_match_only_flag() -> None:
    captured: dict = {"match_only": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--match-only",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["match_only"] is True


def test_order_accepts_execution_mode() -> None:
    captured: dict = {"execution_mode": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--execution-mode", "api",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["execution_mode"] == "api"


def test_order_accepts_matching_risk_policy() -> None:
    captured: dict = {"matching_risk_policy": None, "flagged_match_action": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--matching-risk-policy", "aggressive",
            "--flagged-match-action", "add-to-cart",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["matching_risk_policy"] == "aggressive"
    assert captured["flagged_match_action"] == "add-to-cart"


def test_order_accepts_ai_matching_flags() -> None:
    captured: dict = {
        "ai": None,
        "provider": None,
        "review_model": None,
        "ai_accept_confidence": None,
    }
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--ai",
            "--provider", "rotation",
            "--review-model", "rotation",
            "--ai-accept-confidence", "0.93",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["ai"] is True
    assert captured["provider"] == "rotation"
    assert captured["review_model"] == "rotation"
    assert captured["ai_accept_confidence"] == 0.93


def test_order_accepts_prevented_items_excel_override() -> None:
    captured: dict = {"prevented_items_excel": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--prevented-items-excel",
            "data/input/prevented_items/custom_prevented.xlsx",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["prevented_items_excel"] == \
        "data/input/prevented_items/custom_prevented.xlsx"


def test_order_accepts_manual_review_corrections_source() -> None:
    captured: dict = {"from_manual_review_corrections": None}
    result = _invoke(
        [
            "order",
            "--profile", "wardany",
            "--from-manual-review-corrections", "manual_review.csv",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["from_manual_review_corrections"] == "manual_review.csv"


def test_order_accepts_item_workers_flag() -> None:
    captured: dict = {"item_workers": None}
    result = _invoke(
        [
            "order",
            "--excel", "data.xlsx",
            "--profile", "wardany",
            "--item-workers", "3",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["item_workers"] == 3


def test_order_item_workers_defaults_to_none() -> None:
    captured: dict = {"item_workers": "sentinel"}  # non-None sentinel
    result = _invoke(
        ["order", "--excel", "data.xlsx", "--profile", "wardany"],
        captured,
    )
    assert result.exit_code == 0
    assert captured["item_workers"] is None


# ─────────────────────────── remove-cart ───────────────────────────


def test_remove_cart_accepts_excel_and_debug_browser() -> None:
    captured: dict = {"excel": None, "debug_browser": None}
    result = _invoke(
        [
            "remove-cart",
            "--excel", "data/input/remove_items/remove.xlsx",
            "--profile", "wardany",
            "--debug-browser",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["excel"] == "data/input/remove_items/remove.xlsx"
    assert captured["debug_browser"] is True


def test_remove_cart_accepts_manual_review_source() -> None:
    captured: dict = {"from_manual_review": None, "manual_decision": None}
    result = _invoke(
        [
            "remove-cart",
            "--from-manual-review", "artifacts/order/wardany/run/manual_review.csv",
            "--profile", "wardany",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["from_manual_review"] == \
        "artifacts/order/wardany/run/manual_review.csv"
    assert captured["manual_decision"] == "not_matching"


def test_remove_cart_accepts_all_profiles() -> None:
    captured: dict = {"all_profiles": None}
    result = _invoke(
        [
            "remove-cart",
            "--excel", "data/input/remove_items/remove.xlsx",
            "--all-profiles",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["all_profiles"] is True


def test_remove_cart_accepts_item_workers_flag() -> None:
    captured: dict = {"item_workers": None}
    result = _invoke(
        [
            "remove-cart",
            "--excel", "data/input/remove_items/remove.xlsx",
            "--profile", "wardany",
            "--item-workers", "2",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["item_workers"] == 2


def test_remove_cart_accepts_execution_mode() -> None:
    captured: dict = {"execution_mode": None}
    result = _invoke(
        [
            "remove-cart",
            "--excel", "data/input/remove_items/remove.xlsx",
            "--profile", "wardany",
            "--execution-mode", "browser",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["execution_mode"] == "browser"


# ─────────────────────────── export-products ───────────────────────────


def test_export_products_accepts_output_options() -> None:
    captured: dict = {
        "output_dir": None,
        "stem": None,
        "page_size": None,
        "limit": None,
        "debug_browser": None,
    }
    result = _invoke(
        [
            "export-products",
            "--profile", "wardany",
            "--output-dir", "artifacts/catalog/{profile}",
            "--stem", "catalog",
            "--page-size", "50",
            "--limit", "5",
            "--debug-browser",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["output_dir"] == "artifacts/catalog/{profile}"
    assert captured["stem"] == "catalog"
    assert captured["page_size"] == 50
    assert captured["limit"] == 5
    assert captured["debug_browser"] is True


# ─────────────────────────── match-products ───────────────────────────


def test_match_products_accepts_ai_and_trace_options() -> None:
    captured: dict = {
        "trace": None,
        "no_ai": None,
        "provider": None,
        "concurrency": None,
    }
    result = _invoke(
        [
            "match-products",
            "--profile", "wardany",
            "--excel", "data/input/order_items/ddd.xlsx",
            "--limit", "5",
            "--trace",
            "--no-ai",
            "--provider", "rotation",
            "--review-model", "rotation",
            "--concurrency", "4",
        ],
        captured,
    )
    assert result.exit_code == 0
    assert captured["trace"] is True
    assert captured["no_ai"] is True
    assert captured["provider"] == "rotation"
    assert captured["concurrency"] == 4
