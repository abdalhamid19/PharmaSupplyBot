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

    def test_order_accepts_fast_search_flag(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--fast-search",
            ]
        )

        self.assertTrue(args.fast_search)

    def test_order_accepts_match_only_flag(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--match-only",
            ]
        )

        self.assertTrue(args.match_only)

    def test_order_accepts_ai_matching_flags(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--ai",
                "--provider",
                "rotation",
                "--review-model",
                "rotation",
                "--ai-accept-confidence",
                "0.93",
            ]
        )

        self.assertTrue(args.ai)
        self.assertEqual(args.provider, "rotation")
        self.assertEqual(args.review_model, "rotation")
        self.assertEqual(args.ai_accept_confidence, 0.93)

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

    def test_order_accepts_item_workers_flag(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
                "--item-workers",
                "3",
            ]
        )
        self.assertEqual(args.item_workers, 3)

    def test_order_item_workers_defaults_to_none(self) -> None:
        args = build_parser().parse_args(
            [
                "order",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--profile",
                "wardany",
            ]
        )
        self.assertIsNone(args.item_workers)

    def test_remove_cart_accepts_item_workers_flag(self) -> None:
        args = build_parser().parse_args(
            [
                "remove-cart",
                "--excel",
                "data/input/remove_items/remove.xlsx",
                "--profile",
                "wardany",
                "--item-workers",
                "2",
            ]
        )
        self.assertEqual(args.item_workers, 2)

    def test_export_products_accepts_output_options(self) -> None:
        args = build_parser().parse_args(
            [
                "export-products",
                "--profile",
                "wardany",
                "--output-dir",
                "artifacts/catalog/{profile}",
                "--stem",
                "catalog",
                "--page-size",
                "50",
                "--limit",
                "5",
                "--debug-browser",
            ]
        )
        self.assertEqual(args.cmd, "export-products")
        self.assertEqual(args.output_dir, "artifacts/catalog/{profile}")
        self.assertEqual(args.stem, "catalog")
        self.assertEqual(args.page_size, 50)
        self.assertEqual(args.limit, 5)
        self.assertTrue(args.debug_browser)

    def test_match_products_accepts_ai_and_trace_options(self) -> None:
        args = build_parser().parse_args(
            [
                "match-products",
                "--profile",
                "wardany",
                "--excel",
                "data/input/order_items/ddd.xlsx",
                "--limit",
                "5",
                "--trace",
                "--no-ai",
                "--provider",
                "rotation",
                "--review-model",
                "rotation",
                "--concurrency",
                "4",
            ]
        )

        self.assertEqual(args.cmd, "match-products")
        self.assertTrue(args.trace)
        self.assertTrue(args.no_ai)
        self.assertEqual(args.provider, "rotation")
        self.assertEqual(args.concurrency, 4)


if __name__ == "__main__":
    unittest.main()
