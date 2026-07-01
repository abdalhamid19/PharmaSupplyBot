import unittest
from types import SimpleNamespace

from src.core.config.config_factory import build_runtime_config
from src.tawreed.tawreed_checkout import confirm_order


class _FakePage:
    def __init__(self) -> None:
        self.clicked_selectors: list[str] = []
        self.load_states: list[tuple[str, int]] = []

    def locator(self, selector: str):
        return _FakeLocator(self, selector)

    def wait_for_load_state(self, state: str, timeout: int) -> None:
        self.load_states.append((state, timeout))


class _FakeLocator:
    def __init__(self, page: _FakePage, selector: str) -> None:
        self.page = page
        self.selector = selector

    def click(self) -> None:
        self.page.clicked_selectors.append(self.selector)


class TawreedCheckoutTests(unittest.TestCase):
    def test_runtime_submit_order_defaults_to_false(self) -> None:
        runtime = build_runtime_config({})
        self.assertFalse(runtime.submit_order)

    def test_confirm_order_clicks_checkout_and_final_confirmation(self) -> None:
        selectors = SimpleNamespace(
            checkout_button="#checkout",
            confirm_order_button="#confirm",
        )
        page = _FakePage()

        confirm_order(page, selectors, timeout_ms=45000)

        self.assertEqual(page.clicked_selectors, ["#checkout", "#confirm"])
        self.assertEqual(
            page.load_states,
            [("networkidle", 45000), ("networkidle", 45000)],
        )


if __name__ == "__main__":
    unittest.main()
