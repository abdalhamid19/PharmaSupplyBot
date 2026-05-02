import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.config_models import AppConfig, ExcelConfig, MatchingConfig, ProfileConfig, RuntimeConfig
from src.excel import Item
from src.tawreed import TawreedBot
from src.tawreed_session import SessionInvalidError


class _FakePage:
    def __init__(self, url: str):
        self.url = url


class TawreedBotTests(unittest.TestCase):
    def _bot(self) -> TawreedBot:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={"wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})},
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
            profiles={"wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})},
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

        self.assertTrue(
            bot._is_products_page(_FakePage("https://seller.tawreed.io/#/catalog/store-products/dv/"))
        )
        self.assertFalse(bot._is_products_page(_FakePage("https://seller.tawreed.io/#/login")))

    def test_process_items_stops_before_next_item_when_stop_flag_exists(self) -> None:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={"wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})},
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

            with patch.object(bot, "_process_single_item") as process_item:
                completed = bot._process_items(object(), [])
                self.assertTrue(completed)
                completed = bot._process_items(
                    object(),
                    [SimpleNamespace(code="1", name="Panadol")],
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
                patch("src.tawreed.close_visible_dialogs") as cleanup,
                patch.object(bot, "_record_item_summary") as record_summary,
                patch("src.tawreed.dump_artifacts") as dump_artifacts,
                patch("src.tawreed.visible_overlay_diagnostics", return_value="overlay_panels=1"),
            ):
                if error is None:
                    with patch.object(bot, "_add_item"):
                        bot._process_single_item(object(), item)
                else:
                    with patch.object(bot, "_add_item", side_effect=error):
                        bot._process_single_item(object(), item)

            self.assertEqual(cleanup.call_count, expected_cleanup_calls)
            record_summary.assert_called_once()
            if isinstance(error, RuntimeError) and not isinstance(error, bot.skip_item_exception):
                dump_artifacts.assert_called_once()
                details = dump_artifacts.call_args.kwargs["details"]
                self.assertIn("overlay_diagnostics=overlay_panels=1", details)

    def test_auth_does_not_replace_existing_state_when_validation_fails(self) -> None:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={"wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})},
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

            def fake_save_session_state(_context, path: Path, is_intermediate: bool) -> None:
                path.write_text("new-state", encoding="utf-8")

            with patch("src.tawreed.sync_playwright", return_value=_PlaywrightContext()):
                with patch("src.tawreed.open_auth_page", return_value=(fake_browser, fake_context, fake_page)):
                    with patch("src.tawreed.attempt_env_login"):
                        with patch("src.tawreed.print_auth_instructions"):
                            with patch("src.tawreed.wait_for_login_detection", return_value=True):
                                with patch("src.tawreed.wait_for_network_idle"):
                                    with patch("src.tawreed.print_login_detection_result"):
                                        with patch("src.tawreed.save_session_state", side_effect=fake_save_session_state):
                                            with patch(
                                                "src.tawreed.validate_saved_session",
                                                side_effect=SessionInvalidError("invalid"),
                                            ):
                                                with patch("src.tawreed.close_context"):
                                                    with patch("src.tawreed.close_browser"):
                                                        with self.assertRaises(SessionInvalidError):
                                                            bot.auth_headless(wait_seconds=30)

            self.assertEqual(state_path.read_text(encoding="utf-8"), "old-state")
            self.assertFalse((Path(temp_dir) / "wardany.tmp.json").exists())

    def test_headless_auth_failure_message_is_used_when_login_is_not_detected(self) -> None:
        config = AppConfig(
            base_url="https://seller.tawreed.io/#/login",
            excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
            profiles={"wardany": ProfileConfig(display_name="Wardany", pharmacy_switch={})},
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

            with patch("src.tawreed.sync_playwright", return_value=_PlaywrightContext()):
                with patch("src.tawreed.open_auth_page", return_value=(fake_browser, fake_context, fake_page)):
                    with patch("src.tawreed.attempt_env_login"):
                        with patch("src.tawreed.print_auth_instructions"):
                            with patch("src.tawreed.wait_for_login_detection", return_value=False):
                                with patch("src.tawreed.wait_for_network_idle"):
                                    with patch("src.tawreed.print_login_detection_result"):
                                        with patch("src.tawreed.save_session_state"):
                                            with patch("src.tawreed.dump_artifacts"):
                                                with patch("src.tawreed.close_context"):
                                                    with patch("src.tawreed.close_browser"):
                                                        with self.assertRaises(RuntimeError) as context:
                                                            bot.auth_headless(wait_seconds=30)
            self.assertIn("Headless auth did not produce a valid Tawreed session", str(context.exception))


if __name__ == "__main__":
    unittest.main()
