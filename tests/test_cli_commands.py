import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from src.cli.cli_cart_removal import run_remove_cart_command
from src.cli.cli_order import (
    _load_order_items as load_order_items,
)
from src.cli.cli_order import (
    _prepared_order_items as prepared_order_items,
)
from src.cli.cli_order import (
    _run_parallel_order as run_parallel_order,
)
from src.cli.cli_order import (
    _run_single_profile as run_single_profile,
)
from src.cli.cli_shared import invalid_session_exit
from src.core.utils.excel import Item


class CliCommandsTests(unittest.TestCase):
    def test_resumable_order_items_skips_items_already_in_summary(self) -> None:
        items = [
            Item(code="1", name="Panadol", qty=1),
            Item(code="", name="Devarol", qty=2),
        ]
        args: Any = SimpleNamespace(resume=True)

        with TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                summary_dir = Path("artifacts") / "wardany"
                summary_dir.mkdir(parents=True)
                (summary_dir / "order_result_summary.csv").write_text(
                    "item_code,item_name,status\n1,Panadol,added-to-cart\n",
                    encoding="utf-8",
                )

                with patch("src.cli.cli_order.require_state_file"):
                    from src.cli.cli_order import _prepared_order_items

                    remaining = list(_prepared_order_items("wardany", items, args))
            finally:
                os.chdir(original_cwd)

        self.assertEqual(remaining, [items[1]])

    def test_resumable_match_only_uses_match_only_summary(self) -> None:
        items = [
            Item(code="1", name="Panadol", qty=1),
            Item(code="2", name="Devarol", qty=2),
        ]
        args: Any = SimpleNamespace(resume=True, match_only=True)

        with TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                summary_dir = Path("artifacts") / "wardany"
                summary_dir.mkdir(parents=True)
                (summary_dir / "match_only_summary.csv").write_text(
                    "item_code,item_name,status\n1,Panadol,matched-only\n",
                    encoding="utf-8",
                )
                with patch("src.cli.cli_order.require_state_file"):
                    remaining = list(prepared_order_items("wardany", items, args))
            finally:
                os.chdir(original_cwd)

        self.assertEqual(remaining, [items[1]])

    def test_load_order_items_filters_prevented_items(self) -> None:
        items = [
            Item(code="1", name="Blocked", qty=1),
            Item(code="2", name="Allowed", qty=1),
        ]
        args: Any = SimpleNamespace(
            excel="data/input/order_items/orders.xlsx",
            limit=0,
            prevented_items_excel="data/input/prevented_items/drugprevented.xlsx",
        )

        with (
            patch("src.cli.cli_order.load_items_from_excel", return_value=items),
            patch("pathlib.Path.is_file", return_value=True),
            patch(
                "src.cli.cli_order.load_prevented_items",
                return_value=[SimpleNamespace(code="1", name="Blocked")],
            ),
        ):
            allowed_items = list(load_order_items(_app_config(), args))

        self.assertEqual(allowed_items, [items[1]])

    def test_load_order_items_ignores_missing_prevented_items_file(self) -> None:
        items = [Item(code="1", name="Allowed", qty=1)]
        args: Any = SimpleNamespace(
            excel="data/input/order_items/orders.xlsx",
            limit=0,
            prevented_items_excel="data/input/prevented_items/missing.xlsx",
        )

        with (
            patch("src.cli.cli_order.load_items_from_excel", return_value=items),
            patch("pathlib.Path.is_file", return_value=False),
        ):
            allowed_items = list(load_order_items(_app_config(), args))

        self.assertEqual(allowed_items, items)

    def test_load_order_items_rejects_prevented_file_as_order_excel(self) -> None:
        args: Any = SimpleNamespace(
            excel="data/input/prevented_items/drugprevented.xlsx",
            limit=0,
            prevented_items_excel="data/input/prevented_items/drugprevented.xlsx",
        )

        with self.assertRaisesRegex(SystemExit, "Order Excel cannot be"):
            load_order_items(_app_config(), args)

    def test_run_single_profile_uses_match_only_flow(self) -> None:
        items = [Item(code="1", name="Panadol", qty=1)]
        args: Any = SimpleNamespace(
            excel="data/input/order_items/orders.xlsx",
            limit=0,
            resume=False,
            item_workers=1,
            match_only=True,
            prevented_items_excel="data/input/prevented_items/missing.xlsx",
        )
        app_config: Any = SimpleNamespace(
            base_url="https://seller.tawreed.io/#/login",
            excel=SimpleNamespace(),
            runtime=SimpleNamespace(item_workers=1),
        )

        with (
            patch(
                "src.cli.cli_order.load_match_only_items_from_excel", return_value=items
            ),
            patch("pathlib.Path.is_file", return_value=False),
            patch("src.cli.cli_order.require_state_file"),
            patch("src.cli.cli_order._order_bot", return_value=object()) as build_bot,
            patch("src.cli.cli_order._run_profile_order") as run_order,
            patch("src.cli.cli_order._run_profile_match_only") as run_match_only,
        ):
            profile: Any = SimpleNamespace()
            run_single_profile(app_config, "wardany", profile, args)

        build_bot.assert_called_once()
        run_order.assert_not_called()
        run_match_only.assert_called_once()

    def test_run_single_profile_limits_after_resume_skips_previous_rows(self) -> None:
        items = [
            Item(code=str(index), name=f"Item {index}", qty=1) for index in range(20)
        ]
        captured_items: list[Item] = []
        args: Any = SimpleNamespace(
            excel="data/input/order_items/orders.xlsx",
            limit=10,
            resume=True,
            item_workers=1,
            prevented_items_excel="data/input/prevented_items/missing.xlsx",
        )
        app_config: Any = SimpleNamespace(
            base_url="https://seller.tawreed.io/#/login",
            excel=SimpleNamespace(),
            runtime=SimpleNamespace(item_workers=1),
        )

        with TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                summary_dir = Path("artifacts") / "wardany"
                summary_dir.mkdir(parents=True)
                summary_rows = [
                    f"{index},Item {index},added-to-cart" for index in range(9)
                ]
                (summary_dir / "order_result_summary.csv").write_text(
                    "item_code,item_name,status\n" + "\n".join(summary_rows) + "\n",
                    encoding="utf-8",
                )
                self._run_single_profile_and_capture_items(
                    app_config, args, items, captured_items
                )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(captured_items, items[9:19])

    def _run_single_profile_and_capture_items(
        self,
        app_config: Any,
        args: Any,
        items: list[Item],
        captured_items: list[Item],
    ) -> None:
        with (
            patch(
                "src.cli.cli_order.load_items_from_excel", return_value=items
            ) as load,
            patch("pathlib.Path.is_file", return_value=False),
            patch("src.cli.cli_order.require_state_file"),
            patch("src.cli.cli_order._order_bot", return_value=object()),
            patch("src.cli.cli_order._run_profile_order") as run_order,
        ):
            run_order.side_effect = lambda _base, _key, _bot, order_items: (
                captured_items.extend(list(order_items))
            )
            profile: Any = SimpleNamespace()
            run_single_profile(app_config, "wardany", profile, args)

        self.assertEqual(load.call_args.kwargs["limit"], 0)

    def test_parallel_match_only_merges_match_only_summary(self) -> None:
        items = [
            Item(code="1", name="Panadol", qty=1),
            Item(code="2", name="Devarol", qty=1),
        ]
        args: Any = SimpleNamespace(
            config="config.yaml",
            match_only=True,
            debug_browser=False,
            fast_search=False,
            stop_flag=None,
            warehouse_mode=None,
            min_discount_percent=None,
        )
        app_config: Any = SimpleNamespace(base_url="https://seller.tawreed.io")

        with (
            patch(
                "src.cli.cli_order.multiprocessing.get_context",
                return_value=_InlineContext(),
            ),
            patch(
                "src.cli.item_worker_runner.run_order_chunk",
                return_value={"status": "ok"},
            ),
            patch("src.cli.cli_order.merge_worker_summaries") as merge,
            patch("src.cli.cli_order.report_worker_results") as report,
        ):
            run_parallel_order(app_config, "wardany", items, args, item_workers=2)

        merge.assert_called_once_with("wardany", "match_only_summary")
        report.assert_called_once()

    def test_prepared_order_items_requires_state_then_applies_resume(self) -> None:
        items = [Item(code="1", name="Panadol", qty=1)]
        args: Any = SimpleNamespace(resume=False)

        with (
            patch("src.cli.cli_order.require_state_file") as require_state,
        ):
            prepared = list(prepared_order_items("wardany", items, args))

        self.assertEqual(prepared, items)
        require_state.assert_called_once_with("wardany")

    def test_invalid_session_exit_opens_reauth_and_returns_standard_message(
        self,
    ) -> None:
        error: Any = SimpleNamespace()

        with patch("src.cli.cli_shared.open_reauth_in_browser") as reauth:
            exit_error = invalid_session_exit(
                "https://seller.tawreed.io", "wardany", error
            )

        reauth.assert_called_once_with("https://seller.tawreed.io", "wardany")
        self.assertIsInstance(exit_error, SystemExit)
        self.assertIn("py run.py auth --profile wardany", str(exit_error))

    def test_run_remove_cart_command_invokes_bot_for_selected_profile(self) -> None:
        profile = SimpleNamespace()
        app_config: Any = SimpleNamespace(
            base_url="https://seller.tawreed.io/#/login",
            profiles={"wardany": profile},
            profiles_to_run=lambda profile=None, all_profiles=False: [
                ("wardany", profile)
            ],
        )
        args: Any = SimpleNamespace(
            excel="data/input/remove_items/remove.xlsx",
            profile="wardany",
            all_profiles=False,
            debug_browser=True,
        )

        with (
            patch(
                "src.cli.cli_cart_removal.load_cart_removal_items",
                return_value=[object()],
            ) as load_items,
            patch("src.cli.cli_cart_removal.require_state_file"),
            patch("src.cli.cli_cart_removal.build_bot") as build_bot,
        ):
            bot = build_bot.return_value
            result = run_remove_cart_command(app_config, args)

        self.assertEqual(result, 0)
        load_items.assert_called_once()
        bot.remove_cart_items.assert_called_once()


def _app_config() -> Any:
    return SimpleNamespace(excel=SimpleNamespace())


class _InlineContext:
    def Pool(self, processes: int):
        return _InlinePool(processes)


class _InlinePool:
    def __init__(self, processes: int) -> None:
        self.processes = processes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False

    def map(self, func, payloads):
        return [func(payload) for payload in payloads]


if __name__ == "__main__":
    unittest.main()
