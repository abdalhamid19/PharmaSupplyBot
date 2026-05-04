import os
import unittest
from unittest.mock import patch

from src.ui.streamlit_auth import interactive_auth_available


class StreamlitAuthTests(unittest.TestCase):
    def test_interactive_auth_available_on_windows(self) -> None:
        with patch("src.ui.streamlit_auth.sys.platform", "win32"):
            with patch.dict(os.environ, {}, clear=True):
                self.assertTrue(interactive_auth_available())

    def test_interactive_auth_unavailable_on_linux_without_display(self) -> None:
        with patch("src.ui.streamlit_auth.sys.platform", "linux"):
            with patch.dict(os.environ, {}, clear=True):
                self.assertFalse(interactive_auth_available())

    def test_interactive_auth_available_on_linux_with_display(self) -> None:
        with patch("src.ui.streamlit_auth.sys.platform", "linux"):
            with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
                self.assertTrue(interactive_auth_available())


if __name__ == "__main__":
    unittest.main()
