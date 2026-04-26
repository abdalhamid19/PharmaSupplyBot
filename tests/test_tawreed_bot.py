import unittest
from pathlib import Path
from types import SimpleNamespace

from src.config_models import AppConfig, ExcelConfig, MatchingConfig, ProfileConfig, RuntimeConfig
from src.tawreed import TawreedBot


class _FakePage:
    def __init__(self, url: str):
        self.url = url


class TawreedBotTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
