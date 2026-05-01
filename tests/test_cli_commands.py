import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.cli_commands import load_order_items, resumable_order_items, run_remove_cart_command
from src.excel import Item


class CliCommandsTests(unittest.TestCase):
    def test_resumable_order_items_skips_items_already_in_summary(self) -> None:
        items = [
            Item(code="1", name="Panadol", qty=1),
            Item(code="", name="Devarol", qty=2),
        ]
        args = SimpleNamespace(resume=True)

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

                remaining = resumable_order_items("wardany", items, args)
            finally:
                os.chdir(original_cwd)

        self.assertEqual(remaining, [items[1]])

    def test_load_order_items_filters_prevented_items(self) -> None:
        items = [
            Item(code="1", name="Blocked", qty=1),
            Item(code="2", name="Allowed", qty=1),
        ]
        args = SimpleNamespace(
            excel="input/order_items/orders.xlsx",
            limit=0,
            prevented_items_excel="input/prevented_items/drugprevented.xlsx",
        )

        with (
            patch("src.cli_commands.load_items_from_excel", return_value=items),
            patch("pathlib.Path.is_file", return_value=True),
            patch(
                "src.cli_commands.load_prevented_items",
                return_value=[SimpleNamespace(code="1", name="Blocked")],
            ),
        ):
            allowed_items = load_order_items(SimpleNamespace(excel=SimpleNamespace()), args)

        self.assertEqual(allowed_items, [items[1]])

    def test_load_order_items_ignores_missing_prevented_items_file(self) -> None:
        items = [Item(code="1", name="Allowed", qty=1)]
        args = SimpleNamespace(
            excel="input/order_items/orders.xlsx",
            limit=0,
            prevented_items_excel="input/prevented_items/missing.xlsx",
        )

        with (
            patch("src.cli_commands.load_items_from_excel", return_value=items),
            patch("pathlib.Path.is_file", return_value=False),
        ):
            allowed_items = load_order_items(SimpleNamespace(excel=SimpleNamespace()), args)

        self.assertEqual(allowed_items, items)

    def test_load_order_items_rejects_prevented_file_as_order_excel(self) -> None:
        args = SimpleNamespace(
            excel="input/prevented_items/drugprevented.xlsx",
            limit=0,
            prevented_items_excel="input/prevented_items/drugprevented.xlsx",
        )

        with self.assertRaisesRegex(SystemExit, "Order Excel cannot be"):
            load_order_items(SimpleNamespace(excel=SimpleNamespace()), args)

    def test_run_remove_cart_command_invokes_bot_for_selected_profile(self) -> None:
        profile = SimpleNamespace()
        app_config = SimpleNamespace(
            base_url="https://seller.tawreed.io/#/login",
            profiles={"wardany": profile},
            profiles_to_run=lambda profile=None, all_profiles=False: [("wardany", profile)],
        )
        args = SimpleNamespace(
            excel="input/remove_items/remove.xlsx",
            profile="wardany",
            all_profiles=False,
            debug_browser=True,
        )

        with (
            patch("src.cli_commands.load_cart_removal_items", return_value=[object()]) as load_items,
            patch("src.cli_commands.require_state_file"),
            patch("src.cli_commands.build_bot") as build_bot,
        ):
            bot = build_bot.return_value
            result = run_remove_cart_command(app_config, args)

        self.assertEqual(result, 0)
        load_items.assert_called_once()
        bot.remove_cart_items.assert_called_once()


if __name__ == "__main__":
    unittest.main()
