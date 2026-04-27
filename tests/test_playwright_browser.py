import unittest
from unittest.mock import Mock, patch

from src.playwright_browser import launch_chromium


class PlaywrightBrowserTests(unittest.TestCase):
    def test_launch_chromium_retries_after_missing_executable(self) -> None:
        chromium = Mock()
        chromium.launch.side_effect = [RuntimeError("Executable doesn't exist"), object()]
        playwright = Mock(chromium=chromium)
        with patch("src.playwright_browser._install_chromium") as install_mock:
            launch_chromium(playwright, headless=True, slow_mo_ms=0)
        install_mock.assert_called_once()
        self.assertEqual(chromium.launch.call_count, 2)

    def test_launch_chromium_raises_clear_error_for_missing_linux_library(self) -> None:
        chromium = Mock()
        chromium.launch.side_effect = RuntimeError(
            "error while loading shared libraries: libglib-2.0.so.0: cannot open shared object file"
        )
        playwright = Mock(chromium=chromium)
        with self.assertRaises(RuntimeError) as context:
            launch_chromium(playwright, headless=True, slow_mo_ms=0)
        self.assertIn("Linux runtime libraries are missing", str(context.exception))
        self.assertIn("libglib-2.0.so.0", str(context.exception))


if __name__ == "__main__":
    unittest.main()
