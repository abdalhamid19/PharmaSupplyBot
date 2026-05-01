import unittest
from unittest.mock import patch

from src.streamlit_main import render_main_tabs


class _FakeTab:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class StreamlitMainTests(unittest.TestCase):
    def test_main_tabs_include_prevented_items_page(self) -> None:
        created_tabs = [_FakeTab() for _ in range(5)]
        with (
            patch("src.streamlit_main.st.tabs", return_value=created_tabs) as tabs,
            patch("src.streamlit_main.render_overview"),
            patch("src.streamlit_main.render_auth_tab"),
            patch("src.streamlit_main.render_order_tab"),
            patch("src.streamlit_main.render_prevented_items_tab") as prevented_tab,
            patch("src.streamlit_main.render_results_tab"),
        ):
            render_main_tabs(object(), "wardany", "config.yaml")

        tabs.assert_called_once_with(
            ["Overview", "Auth", "Order", "Prevented items", "Results"]
        )
        prevented_tab.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
