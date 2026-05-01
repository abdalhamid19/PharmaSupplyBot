import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.streamlit_order import order_command
from src.streamlit_order_form import (
    persist_existing_prevented_items_file,
    persist_uploaded_prevented_items,
)


class _FakeUpload:
    def __init__(self, content: bytes):
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


class StreamlitOrderTests(unittest.TestCase):
    def test_order_command_adds_highest_discount_override(self) -> None:
        command = order_command(
            Path("config.yaml"),
            {
                "limit": 5,
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "highest_discount": True,
            },
            Path("input/ddd.xlsx"),
        )

        self.assertIn("--warehouse-mode", command)
        self.assertEqual(command[command.index("--warehouse-mode") + 1], "max_discount")

    def test_order_command_adds_min_discount_override(self) -> None:
        command = order_command(
            Path("config.yaml"),
            {
                "limit": 5,
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "highest_discount": False,
                "min_discount_percent": 12,
            },
            Path("input/ddd.xlsx"),
        )

        self.assertIn("--min-discount-percent", command)
        self.assertEqual(command[command.index("--min-discount-percent") + 1], "12")

    def test_order_command_adds_resume(self) -> None:
        command = order_command(
            Path("config.yaml"),
            {
                "limit": 5,
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "resume": True,
                "highest_discount": False,
                "min_discount_percent": 0,
            },
            Path("input/ddd.xlsx"),
        )

        self.assertIn("--resume", command)

    def test_order_command_adds_prevented_items_excel(self) -> None:
        command = order_command(
            Path("config.yaml"),
            {
                "limit": 5,
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "resume": False,
                "highest_discount": False,
                "min_discount_percent": 0,
                "prevented_items_excel": "input/drugprevented.xlsx",
            },
            Path("input/ddd.xlsx"),
        )

        self.assertIn("--prevented-items-excel", command)
        self.assertEqual(
            command[command.index("--prevented-items-excel") + 1],
            "input/drugprevented.xlsx",
        )

    def test_persist_uploaded_prevented_items_saves_active_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "drugprevented.xlsx"
            saved_path = persist_uploaded_prevented_items(_FakeUpload(b"xlsx-bytes"), path)

            self.assertEqual(saved_path, path)
            self.assertEqual(path.read_bytes(), b"xlsx-bytes")

    def test_persist_existing_prevented_items_file_saves_active_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.xlsx"
            target_path = Path(temp_dir) / "drugprevented.xlsx"
            source_path.write_bytes(b"xlsx-bytes")

            saved_path = persist_existing_prevented_items_file(source_path, target_path)

            self.assertEqual(saved_path, target_path)
            self.assertEqual(target_path.read_bytes(), b"xlsx-bytes")


if __name__ == "__main__":
    unittest.main()
