import unittest

from src.cli_parser import build_parser


class CliParserTests(unittest.TestCase):
    def test_auth_accepts_headless_flag(self) -> None:
        args = build_parser().parse_args(["auth", "--profile", "wardany", "--headless"])
        self.assertTrue(args.headless)

    def test_order_accepts_debug_browser_flag(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "input/ddd.xlsx",
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
                "input/ddd.xlsx",
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
                "input/ddd.xlsx",
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
                "input/ddd.xlsx",
                "--profile",
                "wardany",
                "--resume",
                "--stop-flag",
                "artifacts/run_control/order_stop.flag",
            ]
        )

        self.assertTrue(args.resume)
        self.assertEqual(args.stop_flag, "artifacts/run_control/order_stop.flag")

    def test_auth_does_not_expose_debug_browser_flag(self) -> None:
        args = build_parser().parse_args(["auth", "--profile", "wardany"])
        self.assertFalse(hasattr(args, "debug_browser"))


if __name__ == "__main__":
    unittest.main()
