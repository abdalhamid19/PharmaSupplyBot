import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.streamlit_order import order_command
from src import streamlit_order
from src.streamlit_order_form import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    add_and_save_prevented_item,
    order_form_fields,
    order_excel_options,
    prevented_excel_options,
    persist_existing_prevented_items_file,
    persist_uploaded_prevented_items,
)
from src.prevented_items import PreventedItem, load_prevented_items


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
            Path("data/input/order_items/ddd.xlsx"),
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
            Path("data/input/order_items/ddd.xlsx"),
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
            Path("data/input/order_items/ddd.xlsx"),
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
                "prevented_items_excel": "data/input/prevented_items/drugprevented.xlsx",
            },
            Path("data/input/order_items/ddd.xlsx"),
        )

        self.assertIn("--prevented-items-excel", command)
        self.assertEqual(
            command[command.index("--prevented-items-excel") + 1],
            "data/input/prevented_items/drugprevented.xlsx",
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

    def test_order_excel_options_excludes_default_prevented_items_file(self) -> None:
        with patch(
            "src.streamlit_order_form.available_excel_options",
            return_value=[
                "data/input/order_items/shortage_report_total_20260426.xlsx",
            ],
        ):
            options = order_excel_options()

        self.assertEqual(options, ["data/input/order_items/shortage_report_total_20260426.xlsx"])

    def test_prevented_excel_options_reads_prevented_items_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            prevented_dir = Path(temp_dir) / "prevented_items"
            prevented_dir.mkdir()
            prevented_path = prevented_dir / "drugprevented.xlsx"
            prevented_path.write_bytes(b"")

            with patch("src.streamlit_order_form.PREVENTED_ITEMS_DIR", prevented_dir):
                options = prevented_excel_options(prevented_path)

        self.assertEqual(options, [str(prevented_path)])

    def test_order_form_fields_uses_default_prevented_items_path(self) -> None:
        with (
            patch(
                "src.streamlit_order_form.excel_source_fields",
                return_value=("Existing file", "data/input/order_items/orders.xlsx", None),
            ),
            patch(
                "src.streamlit_order_form.profile_run_fields",
                return_value=("Single profile", "wardany", 5, False, True, False, 0),
            ),
        ):
            values = order_form_fields(object())

        self.assertEqual(values["prevented_items_excel"], str(DEFAULT_PREVENTED_ITEMS_PATH))

    def test_add_and_save_prevented_item_persists_new_item(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "drugprevented.xlsx"
            updated_items = add_and_save_prevented_item(
                [PreventedItem(code="1", name="Panadol")],
                "2",
                "Devarol",
                path,
            )
            reloaded_items = load_prevented_items(path)

        self.assertEqual(
            updated_items,
            [PreventedItem(code="1", name="Panadol"), PreventedItem(code="2", name="Devarol")],
        )
        self.assertEqual(reloaded_items, updated_items)

    def test_render_order_tab_rejects_prevented_file_as_order_excel(self) -> None:
        form_values = {
            "excel_path_str": "data/input/prevented_items/drugprevented.xlsx",
            "upload": None,
            "prevented_items_excel": "data/input/prevented_items/drugprevented.xlsx",
        }
        with (
            patch("src.streamlit_order.render_running_order_controls", return_value=False),
            patch("src.streamlit_order.order_form_values", return_value=(True, form_values)),
            patch("src.streamlit_order.st.subheader"),
            patch("src.streamlit_order.st.error") as error,
            patch("src.streamlit_order.run_order_submission") as run_submission,
        ):
            streamlit_order.render_order_tab(
                SimpleNamespace(profiles={"wardany": object()}),
                "wardany",
                Path("config.yaml"),
            )

        error.assert_called_once()
        run_submission.assert_not_called()


if __name__ == "__main__":
    unittest.main()
