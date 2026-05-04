import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.ui.streamlit_remove_cart import remove_cart_command, remove_excel_options


class StreamlitRemoveCartTests(unittest.TestCase):
    def test_remove_cart_command_builds_cli_args(self) -> None:
        command = remove_cart_command(
            Path("config.yaml"),
            {
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": True,
            },
            Path("data/input/remove_items/remove.xlsx"),
        )

        self.assertEqual(
            command,
            [
                "remove-cart",
                "--config",
                str(Path("config.yaml")),
                "--excel",
                str(Path("data/input/remove_items/remove.xlsx")),
                "--profile",
                "wardany",
                "--debug-browser",
            ],
        )

    def test_remove_excel_options_reads_remove_items_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            remove_dir = Path(temp_dir) / "remove_items"
            remove_dir.mkdir()
            remove_path = remove_dir / "remove.xlsx"
            remove_path.write_bytes(b"")

            with patch("src.ui.streamlit_remove_cart.REMOVE_ITEMS_DIR", remove_dir):
                options = remove_excel_options()

        self.assertEqual(options, [str(remove_path)])


if __name__ == "__main__":
    unittest.main()
