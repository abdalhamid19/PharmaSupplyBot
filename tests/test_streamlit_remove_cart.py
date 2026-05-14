import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.ui.streamlit_remove_cart import (
    remove_cart_command,
    remove_excel_options,
    start_remove_cart_process,
)


class StreamlitRemoveCartTests(unittest.TestCase):
    def test_remove_cart_command_builds_cli_args(self) -> None:
        command = remove_cart_command(
            Path("config.yaml"),
            {
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": True,
                "execution_mode": "browser",
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
                "--execution-mode",
                "browser",
            ],
        )

    def test_remove_cart_command_adds_item_workers_when_parallel(self) -> None:
        command = remove_cart_command(
            Path("config.yaml"),
            {
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "item_workers": 2,
            },
            Path("data/input/remove_items/remove.xlsx"),
        )

        self.assertIn("--item-workers", command)
        self.assertEqual(command[command.index("--item-workers") + 1], "2")

    def test_start_remove_cart_process_adds_stop_flag(self) -> None:
        with TemporaryDirectory() as temp_dir:
            stop_flag = Path(temp_dir) / "remove_cart_stop.flag"
            stop_flag.write_text("old", encoding="utf-8")
            state = {
                "process": object(),
                "output_path": str(Path(temp_dir) / "out.log"),
            }
            with (
                patch(
                    "src.ui.streamlit_remove_cart.start_cli_subprocess",
                    return_value=state,
                ) as start,
                patch("src.ui.streamlit_remove_cart.st.session_state", {}),
            ):
                start_remove_cart_process(["remove-cart"], stop_flag)

        command = start.call_args.args[0]
        self.assertIn("--stop-flag", command)
        self.assertEqual(command[command.index("--stop-flag") + 1], str(stop_flag))
        self.assertFalse(stop_flag.exists())

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
