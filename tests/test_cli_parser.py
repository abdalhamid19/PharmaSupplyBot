import unittest

from src.cli_parser import build_parser


class CliParserTests(unittest.TestCase):
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

    def test_auth_does_not_expose_debug_browser_flag(self) -> None:
        args = build_parser().parse_args(["auth", "--profile", "wardany"])
        self.assertFalse(hasattr(args, "debug_browser"))


if __name__ == "__main__":
    unittest.main()
