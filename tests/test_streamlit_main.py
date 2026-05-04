import unittest
from unittest.mock import patch

from src.ui.streamlit_main import render_main_tabs


class _FakeTab:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class StreamlitMainTests(unittest.TestCase):
    def test_main_tabs_include_prevented_items_page(self) -> None:
        created_tabs = [_FakeTab() for _ in range(6)]
        app_config = object()
        with (
            patch("src.ui.streamlit_main.st.tabs", return_value=created_tabs) as tabs,
            patch("src.ui.streamlit_main.render_overview"),
            patch("src.ui.streamlit_main.render_auth_tab"),
            patch("src.ui.streamlit_main.render_order_tab"),
            patch("src.ui.streamlit_main.render_prevented_items_tab") as prevented_tab,
            patch("src.ui.streamlit_main.render_remove_cart_tab") as remove_cart_tab,
            patch("src.ui.streamlit_main.render_results_tab"),
        ):
            render_main_tabs(app_config, "wardany", "config.yaml")

        tabs.assert_called_once_with(
            ["Overview", "Auth", "Order", "Prevented items", "Remove cart items", "Results"]
        )
        prevented_tab.assert_called_once_with()
        remove_cart_tab.assert_called_once_with(app_config, "wardany", "config.yaml")


if __name__ == "__main__":
    unittest.main()
