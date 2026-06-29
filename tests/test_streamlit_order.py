import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.core.prevented_items import PreventedItem, load_prevented_items
from src.ui import streamlit_order
from src.ui.streamlit_order import order_command, order_run_summary_csv_path
from src.ui.streamlit_prevented_items import (
    add_and_save_prevented_item,
    persist_existing_prevented_items_file,
    persist_uploaded_prevented_items,
    prevented_excel_options,
)
from src.ui.streamlit_order import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    order_form_fields,
)
from src.ui.streamlit_excel_fields import order_excel_options


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

    def test_order_command_adds_match_only_flag(self) -> None:
        command = order_command(
            Path("config.yaml"),
            {
                "limit": 5,
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "resume": False,
                "match_only": True,
                "execution_mode": "api",
                "highest_discount": False,
                "min_discount_percent": 0,
            },
            Path("data/input/order_items/ddd.xlsx"),
        )

        self.assertIn("--match-only", command)
        self.assertEqual(command[command.index("--execution-mode") + 1], "api")

    def test_order_command_promotes_match_only_auto_to_api(self) -> None:
        command = order_command(
            Path("config.yaml"),
            {
                "limit": 5,
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "resume": False,
                "match_only": True,
                "execution_mode": "auto",
                "highest_discount": False,
                "min_discount_percent": 0,
            },
            Path("data/input/order_items/ddd.xlsx"),
        )

        self.assertEqual(command[command.index("--execution-mode") + 1], "api")

    def test_order_command_adds_matching_risk_flags(self) -> None:
        command = order_command(
            Path("config.yaml"),
            {
                "limit": 5,
                "profile_mode": "Single profile",
                "profile_key": "wardany",
                "debug_browser": False,
                "highest_discount": False,
                "matching_risk_policy": "aggressive",
                "flagged_match_action": "add-to-cart",
            },
            Path("data/input/order_items/ddd.xlsx"),
        )

        self.assertEqual(command[command.index("--matching-risk-policy") + 1], "aggressive")
        self.assertEqual(command[command.index("--flagged-match-action") + 1], "add-to-cart")

    def test_order_command_adds_ai_flags(self) -> None:
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
                "enable_order_ai": True,
                "ai_provider": "rotation",
                "ai_review_model": "rotation",
                "ai_concurrency": 2,
                "ai_verify_policy": "score",
                "ai_search_policy": "safe",
                "ai_accept_confidence": 0.93,
                "ai_review_threshold": 0.97,
            },
            Path("data/input/order_items/ddd.xlsx"),
        )

        self.assertIn("--ai", command)
        self.assertEqual(command[command.index("--provider") + 1], "rotation")
        self.assertEqual(command[command.index("--review-model") + 1], "rotation")
        self.assertEqual(command[command.index("--ai-accept-confidence") + 1], "0.93")

    def test_order_run_summary_path_uses_match_only_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            artifacts = Path(temp_dir) / "artifacts"
            with patch("src.ui.streamlit_order.ARTIFACTS_DIR", artifacts):
                path = order_run_summary_csv_path("wardany", {"match_only": True})

        self.assertEqual(path, Path("artifacts") / "wardany" / "match_only_summary.csv")

    def test_order_run_summary_path_uses_newest_run_folder(self) -> None:
        with TemporaryDirectory() as temp_dir:
            artifacts = Path(temp_dir) / "artifacts"
            run_dir = artifacts / "order/wardany/20260513_1900"
            run_dir.mkdir(parents=True)
            summary = run_dir / "match_only_summary_20260513_1900.csv"
            summary.write_text("item_code\n1\n", encoding="utf-8")
            with patch("src.ui.streamlit_order.ARTIFACTS_DIR", artifacts):
                path = order_run_summary_csv_path("wardany", {"match_only": True})

        self.assertEqual(path, summary)

    def test_order_command_adds_item_workers_when_parallel(self) -> None:
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
                "item_workers": 3,
            },
            Path("data/input/order_items/ddd.xlsx"),
        )

        self.assertIn("--item-workers", command)
        self.assertEqual(command[command.index("--item-workers") + 1], "3")

    def test_order_command_adds_single_item_worker_override(self) -> None:
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
                "item_workers": 1,
            },
            Path("data/input/order_items/ddd.xlsx"),
        )

        self.assertIn("--item-workers", command)
        self.assertEqual(command[command.index("--item-workers") + 1], "1")

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
            saved_path = persist_uploaded_prevented_items(
                _FakeUpload(b"xlsx-bytes"), path
            )

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
            "src.ui.streamlit_excel_fields.available_excel_options",
            return_value=[
                "data/input/order_items/shortage_report_total_20260426.xlsx",
            ],
        ):
            options = order_excel_options()

        self.assertEqual(
            options, ["data/input/order_items/shortage_report_total_20260426.xlsx"]
        )

    def test_prevented_excel_options_reads_prevented_items_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            prevented_dir = Path(temp_dir) / "prevented_items"
            prevented_dir.mkdir()
            prevented_path = prevented_dir / "drugprevented.xlsx"
            prevented_path.write_bytes(b"")

            with patch(
                "src.ui.streamlit_prevented_items.PREVENTED_ITEMS_DIR", prevented_dir
            ):
                options = prevented_excel_options(prevented_path)

        self.assertEqual(options, [str(prevented_path)])

    def test_order_form_fields_uses_default_prevented_items_path(self) -> None:
        with (
            patch(
                "src.ui.streamlit_order.excel_source_fields",
                return_value=(
                    "Existing file",
                    "data/input/order_items/orders.xlsx",
                    None,
                ),
            ),
            patch(
                "src.ui.streamlit_order.profile_run_fields_with_workers",
                return_value=(
                    (
                        "Single profile",
                        "wardany",
                        5,
                        False,
                        True,
                        True,
                        "auto",
                        False,
                        0.0,
                    ),
                    2,
                ),
            ),
        ):
            values = order_form_fields(object())

        self.assertEqual(
            values["prevented_items_excel"], str(DEFAULT_PREVENTED_ITEMS_PATH)
        )
        self.assertEqual(values["item_workers"], 2)
        self.assertTrue(values["match_only"])

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
            [
                PreventedItem(code="1", name="Panadol"),
                PreventedItem(code="2", name="Devarol"),
            ],
        )
        self.assertEqual(reloaded_items, updated_items)

    def test_render_order_tab_rejects_prevented_file_as_order_excel(self) -> None:
        form_values = {
            "excel_path_str": "data/input/prevented_items/drugprevented.xlsx",
            "upload": None,
            "prevented_items_excel": "data/input/prevented_items/drugprevented.xlsx",
        }
        with (
            patch(
                "src.ui.streamlit_order.render_running_order_controls",
                return_value=False,
            ),
            patch(
                "src.ui.streamlit_order.order_form_values",
                return_value=(True, form_values),
            ),
            patch("src.ui.streamlit_order.st.subheader"),
            patch("src.ui.streamlit_order.st.error") as error,
            patch("src.ui.streamlit_order.run_order_submission") as run_submission,
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
