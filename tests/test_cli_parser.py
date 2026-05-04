import unittest

from src.cli.cli_parser import build_parser


class CliParserTests(unittest.TestCase):
    def test_auth_accepts_headless_flag(self) -> None:
        args = build_parser().parse_args(["auth", "--profile", "wardany", "--headless"])
        self.assertTrue(args.headless)

    def test_order_accepts_debug_browser_flag(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--debug-browser",
            ]
        )
        self.assertTrue(args.debug_browser)
        self.assertEqual(args.cmd, "order")

    def test_order_accepts_warehouse_mode_override(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--warehouse-mode",
                "max_discount",
            ]
        )

        self.assertEqual(args.warehouse_mode, "max_discount")

    def test_order_accepts_min_discount_override(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--min-discount-percent",
                "12",
            ]
        )

        self.assertEqual(args.min_discount_percent, 12)

    def test_order_accepts_resume_and_stop_flag(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--resume",
                "--stop-flag",
                "artifacts/run_control/order_stop.flag",
            ]
        )

        self.assertTrue(args.resume)
        self.assertEqual(args.stop_flag, "artifacts/run_control/order_stop.flag")

    def test_order_accepts_prevented_items_excel_override(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--prevented-items-excel",
                "data/input/prevented_items/custom_prevented.xlsx",
            ]
        )

        self.assertEqual(
            args.prevented_items_excel,
            "data/input/prevented_items/custom_prevented.xlsx",
        )

    def test_remove_cart_accepts_excel_and_debug_browser(self) -> None:
        args = build_parser().parse_args(
            [
                "remove-cart",
                "--excel",
                "data/input/remove_items/remove.xlsx",
                "--profile",
                "wardany",
                "--debug-browser",
            ]
        )

        self.assertEqual(args.cmd, "remove-cart")
        self.assertEqual(args.excel, "data/input/remove_items/remove.xlsx")
        self.assertTrue(args.debug_browser)

    def test_remove_cart_accepts_all_profiles(self) -> None:
        args = build_parser().parse_args(
            [
                "remove-cart",
                "--excel",
                "data/input/remove_items/remove.xlsx",
                "--all-profiles",
            ]
        )

        self.assertTrue(args.all_profiles)

    def test_auth_does_not_expose_debug_browser_flag(self) -> None:
        args = build_parser().parse_args(["auth", "--profile", "wardany"])
        self.assertFalse(hasattr(args, "debug_browser"))


if __name__ == "__main__":
    unittest.main()
