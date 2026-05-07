import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from src.core.config.config_models import (
    AppConfig,
    ExcelConfig,
    MatchingConfig,
    ProfileConfig,
    RuntimeConfig,
)
from src.core.matching_models import MatchDecision, SearchMatch
from src.core.utils.excel import Item
from src.tawreed.tawreed import TawreedBot
from src.tawreed.tawreed_session import SessionInvalidError


class _FakePage:
    def __init__(self, url: str):
        self.url = url


class TawreedBotTests(unittest.TestCase):
    def _bot(self) -> TawreedBot:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={
                "wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})
            },
            selectors={"order_flow": {"item_search_input": "#search"}},
            warehouse_strategy={},
            matching=MatchingConfig(),
            runtime=RuntimeConfig(),
        )
        return TawreedBot(
            config=config,
            profile_key="wardany",
            profile=config.profiles["wardany"],
            state_path=Path("state/wardany.json"),
        )

    def test_products_page_detection_uses_url_not_selector_literal(self) -> None:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={
                "wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})
            },
            selectors={
                "order_flow": {
                    "item_search_input": "input[placeholder*='Search']",
                }
            },
            warehouse_strategy={},
            matching=MatchingConfig(),
            runtime=RuntimeConfig(),
        )
        bot = TawreedBot(
            config=config,
            profile_key="wardany",
            profile=config.profiles["wardany"],
            state_path=Path("state/wardany.json"),
        )

        products_page: Any = _FakePage(
            "https://seller.tawreed.io/#/catalog/store-products/dv/"
        )
        login_page: Any = _FakePage("https://seller.tawreed.io/#/login")

        self.assertTrue(bot._is_products_page(products_page))
        self.assertFalse(bot._is_products_page(login_page))

    def test_process_items_stops_before_next_item_when_stop_flag_exists(self) -> None:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={
                "wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})
            },
            selectors={"order_flow": {"item_search_input": "#search"}},
            warehouse_strategy={},
            matching=MatchingConfig(),
            runtime=RuntimeConfig(),
        )
        with TemporaryDirectory() as temp_dir:
            stop_flag = Path(temp_dir) / "stop.flag"
            stop_flag.write_text("stop", encoding="utf-8")
            bot = TawreedBot(
                config=config,
                profile_key="wardany",
                profile=config.profiles["wardany"],
                state_path=Path("state/wardany.json"),
                stop_flag_path=stop_flag,
            )

            page: Any = object()
            with patch.object(bot, "_process_single_item") as process_item:
                completed = bot._process_items(page, [])
                self.assertFalse(completed)
                completed = bot._process_items(
                    page,
                    [Item(code="1", name="Panadol", qty=1)],
                )

            self.assertFalse(completed)
            process_item.assert_not_called()

    def test_process_single_item_cleans_up_on_success_skip_and_failure(self) -> None:
        item = Item(code="1", name="Panadol", qty=1)
        scenarios = (
            ("success", None, 2),
            ("skip", self._bot().skip_item_exception("skip item"), 2),
            ("failure", RuntimeError("technical failure"), 2),
        )

        for _label, error, expected_cleanup_calls in scenarios:
            bot = self._bot()
            with (
                patch("src.tawreed.tawreed.close_visible_dialogs") as cleanup,
                patch.object(bot, "_record_item_summary") as record_summary,
                patch("src.tawreed.tawreed.dump_artifacts") as dump_artifacts,
                patch(
                    "src.tawreed.tawreed.visible_overlay_diagnostics",
                    return_value="overlay_panels=1",
                ),
            ):
                if error is None:
                    page: Any = object()
                    with patch.object(bot, "_add_item"):
                        bot._process_single_item(page, item)
                else:
                    page = object()
                    with patch.object(bot, "_add_item", side_effect=error):
                        bot._process_single_item(page, item)

            self.assertEqual(cleanup.call_count, expected_cleanup_calls)
            record_summary.assert_called_once()
            if isinstance(error, RuntimeError) and not isinstance(
                error, bot.skip_item_exception
            ):
                dump_artifacts.assert_called_once()
                details = dump_artifacts.call_args.kwargs["details"]
                self.assertIn("overlay_diagnostics=overlay_panels=1", details)

    def test_match_only_item_records_summary_without_adding_to_cart(self) -> None:
        bot = self._bot()
        item = Item(code="1", name="Panadol", qty=3)
        page: Any = _FakePage("https://seller.tawreed.io/#/catalog/store-products/dv/")
        match = SearchMatch(
            query="Panadol",
            row_index=0,
            score=20.0,
            data={"productNameEn": "Panadol", "productName": "بنادول"},
        )

        with (
            patch("src.tawreed.tawreed.close_visible_dialogs") as cleanup,
            patch("src.tawreed.tawreed.require_product_match") as require_match,
            patch("src.tawreed.tawreed.append_match_only_summary") as append_summary,
            patch.object(bot, "_add_item") as add_item,
        ):
            require_match.return_value = (match, "Panadol")
            processed = bot._process_single_match_only_item(page, item)

        self.assertTrue(processed)
        add_item.assert_not_called()
        cleanup.assert_called()
        require_match.assert_called_once_with(bot, page, item, require_available=False)
        append_summary.assert_called_once()
        summary = append_summary.call_args.args[2]
        self.assertEqual(summary.status, "matched-only")
        self.assertEqual(summary.ordered_total_qty, 0)

    def test_match_only_accepts_ready_search_surface_without_products_url(self) -> None:
        bot = self._bot()
        item = Item(code="1", name="Panadol", qty=1)
        page: Any = _FakePage("https://seller.tawreed.io/#/purchase/orders/new")
        match = SearchMatch(
            query="Panadol",
            row_index=0,
            score=20.0,
            data={"productNameEn": "Panadol", "productName": "بنادول"},
        )

        with (
            patch.object(bot, "_order_surface_ready", return_value=True),
            patch(
                "src.tawreed.tawreed.require_product_match", return_value=(match, "")
            ) as require_match,
        ):
            bot._match_item_only(page, item)

        require_match.assert_called_once_with(bot, page, item, require_available=False)

    def test_build_item_summary_populates_matched_names_by_language(self) -> None:
        bot = self._bot()
        bot.last_match_decision = MatchDecision(
            best_match=SearchMatch(
                query="Panadol Extra",
                row_index=0,
                score=22.5,
                data={
                    "productNameEn": "Panadol Extra 24 Tabs",
                    "productName": "بنادول اكسترا 24 قرص",
                },
            ),
            diagnostics=[],
            final_reason="Accepted",
        )

        summary = bot._build_item_summary(
            status="added-to-cart",
            reason="Added to cart.",
            elapsed=1.0,
            match_elapsed=0.5,
        )

        self.assertEqual(summary.matched_product_english_name, "Panadol Extra 24 Tabs")
        self.assertEqual(summary.matched_product_english_name_source, "site")
        self.assertEqual(summary.matched_product_arabic_name, "بنادول اكسترا 24 قرص")
        self.assertEqual(summary.matched_query, "Panadol Extra")

    def test_build_item_summary_uses_dom_fallback_english_name(self) -> None:
        bot = self._bot()
        bot.last_match_decision = MatchDecision(
            best_match=SearchMatch(
                query="BEBELAC AR MILK",
                row_index=0,
                score=16.0,
                data={
                    "productNameEn": "",
                    "productNameEnFallback": "BEBELAC AR MILK",
                    "productNameEnSynthetic": True,
                    "productName": "لبن بيبلاك بريماتيور",
                },
            ),
            diagnostics=[],
            final_reason="Accepted",
        )

        summary = bot._build_item_summary(
            status="added-to-cart",
            reason="Added to cart.",
            elapsed=1.0,
            match_elapsed=0.5,
        )

        self.assertEqual(summary.matched_product_english_name, "BEBELAC AR MILK")
        self.assertEqual(summary.matched_product_english_name_source, "fallback")
        self.assertEqual(summary.matched_product_arabic_name, "لبن بيبلاك بريماتيور")

    def test_auth_does_not_replace_existing_state_when_validation_fails(self) -> None:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={
                "wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})
            },
            selectors={
                "login": {
                    "email_input": "#email",
                    "password_input": "#password",
                    "submit_button": "#submit",
                },
                "nav": {"logged_in_marker": "#marker"},
                "order_flow": {"item_search_input": "#search"},
            },
            warehouse_strategy={},
            matching=MatchingConfig(),
            runtime=RuntimeConfig(),
        )
        with TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "wardany.json"
            state_path.write_text("old-state", encoding="utf-8")
            bot = TawreedBot(
                config=config,
                profile_key="wardany",
                profile=config.profiles["wardany"],
                state_path=state_path,
            )

            class _PlaywrightContext:
                def __enter__(self):
                    return object()

                def __exit__(self, exc_type, exc, tb):
                    return False

            fake_context = object()
            fake_browser = object()
            fake_page = object()

            def fake_save_session_state(
                _context, path: Path, is_intermediate: bool
            ) -> None:
                path.write_text("new-state", encoding="utf-8")

            with patch(
                "playwright.sync_api.sync_playwright", return_value=_PlaywrightContext()
            ):
                with patch(
                    "src.tawreed.tawreed_session.open_auth_page",
                    return_value=(fake_browser, fake_context, fake_page),
                ):
                    with patch("src.tawreed.tawreed_session.attempt_env_login"):
                        with patch(
                            "src.tawreed.tawreed_session.print_auth_instructions"
                        ):
                            with patch(
                                "src.tawreed.tawreed_session.wait_for_login_detection",
                                return_value=True,
                            ):
                                with patch(
                                    "src.tawreed.tawreed_session.wait_for_network_idle"
                                ):
                                    with patch(
                                        "src.tawreed.tawreed_session.print_login_detection_result"
                                    ):
                                        with patch(
                                            "src.tawreed.tawreed_session.save_session_state",
                                            side_effect=fake_save_session_state,
                                        ):
                                            with patch(
                                                "src.tawreed.tawreed_session.validate_saved_session",
                                                side_effect=SessionInvalidError(
                                                    "invalid"
                                                ),
                                            ):
                                                with patch(
                                                    "src.tawreed.tawreed_session.close_context"
                                                ):
                                                    with patch(
                                                        "src.tawreed.tawreed_session.close_browser"
                                                    ):
                                                        with self.assertRaises(
                                                            SessionInvalidError
                                                        ):
                                                            bot.auth_headless(
                                                                wait_seconds=30
                                                            )

            self.assertEqual(state_path.read_text(encoding="utf-8"), "old-state")
            self.assertFalse((Path(temp_dir) / "wardany.tmp.json").exists())

    def test_headless_auth_failure_message_is_used_when_login_is_not_detected(
        self,
    ) -> None:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={
                "wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})
            },
            selectors={
                "login": {
                    "email_input": "#email",
                    "password_input": "#password",
                    "submit_button": "#submit",
                },
                "nav": {"logged_in_marker": "#marker"},
                "order_flow": {"item_search_input": "#search"},
            },
            warehouse_strategy={},
            matching=MatchingConfig(),
            runtime=RuntimeConfig(),
        )
        with TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "wardany.json"
            bot = TawreedBot(
                config=config,
                profile_key="wardany",
                profile=config.profiles["wardany"],
                state_path=state_path,
            )

            class _PlaywrightContext:
                def __enter__(self):
                    return object()

                def __exit__(self, exc_type, exc, tb):
                    return False

            fake_context = object()
            fake_browser = object()
            fake_page = object()

            with patch(
                "playwright.sync_api.sync_playwright", return_value=_PlaywrightContext()
            ):
                with patch(
                    "src.tawreed.tawreed_session.open_auth_page",
                    return_value=(fake_browser, fake_context, fake_page),
                ):
                    with patch("src.tawreed.tawreed_session.attempt_env_login"):
                        with patch(
                            "src.tawreed.tawreed_session.print_auth_instructions"
                        ):
                            with patch(
                                "src.tawreed.tawreed_session.wait_for_login_detection",
                                return_value=False,
                            ):
                                with patch(
                                    "src.tawreed.tawreed_session.wait_for_network_idle"
                                ):
                                    with patch(
                                        "src.tawreed.tawreed_session.print_login_detection_result"
                                    ):
                                        with patch(
                                            "src.tawreed.tawreed_session.save_session_state"
                                        ):
                                            with patch(
                                                "src.tawreed.tawreed_artifacts.dump_artifacts"
                                            ):
                                                with patch(
                                                    "src.tawreed.tawreed_session.close_context"
                                                ):
                                                    with patch(
                                                        "src.tawreed.tawreed_session.close_browser"
                                                    ):
                                                        with self.assertRaises(
                                                            RuntimeError
                                                        ) as context:
                                                            bot.auth_headless(
                                                                wait_seconds=30
                                                            )
            self.assertIn(
                "Headless auth did not produce a valid Tawreed session",
                str(context.exception),
            )


if __name__ == "__main__":
    unittest.main()
