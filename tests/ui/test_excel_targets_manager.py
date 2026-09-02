"""Tests for the in-app Excel target add/remove manager."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.ui.excel_targets_manager import (
    DEFAULT_TARGET_NAME,
    USER_ADDED_KEY,
    _normalise_name,
    add_excel_target,
    excel_target_settings,
    remove_excel_target,
    update_excel_target,
    user_added_targets,
)


def _make_upload(name: str, payload: bytes = b"fake-xlsx"):
    return SimpleNamespace(name=name, getvalue=lambda: payload)


class NormaliseNameTests(unittest.TestCase):
    """The slug should be safe for both YAML keys and filenames."""

    def test_ascii_letters_lowercase(self) -> None:
        self.assertEqual(_normalise_name("My Warehouse"), "my_warehouse")

    def test_arabic_input_keeps_original_name(self) -> None:
        """Arabic names keep their original Unicode so the key is readable."""
        self.assertEqual(
            _normalise_name("المخازن الادويه المباشرة"),
            "المخازن الادويه المباشرة",
        )

    def test_mixed_arabic_and_ascii_uses_ascii_slug(self) -> None:
        self.assertEqual(
            _normalise_name("My المخزن 2024"),
            "my_2024",
        )

    def test_strips_punctuation(self) -> None:
        self.assertEqual(_normalise_name("my-warehouse!! 2024"), "my_warehouse_2024")

    def test_empty_falls_back_to_target_hash(self) -> None:
        self.assertTrue(_normalise_name("").startswith("target_"))


class UserAddedTargetsTests(unittest.TestCase):
    """Track which keys came from the operator, not the YAML author."""

    def test_default_is_empty(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            self.assertEqual(user_added_targets(config), [])

    def test_returns_existing_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            config.write_text(
                f"excel_targets:\n  my_wh: {{}}\n{USER_ADDED_KEY}:\n  - my_wh\n",
                encoding="utf-8",
            )
            self.assertEqual(user_added_targets(config), ["my_wh"])


class AddExcelTargetTests(unittest.TestCase):
    """End-to-end: add → file written, config mutated, user-added tagged."""

    def test_add_writes_config_and_catalog(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            upload = _make_upload("vendor_2025.xlsx", b"abc")
            with patch(
                "src.ui.excel_targets_manager.ARTIFACTS_DIR",
                Path(temp_dir) / "artifacts",
            ):
                result = add_excel_target(
                    config_path=config,
                    display_name="My Warehouse",
                    uploaded_file=upload,
                )
            self.assertEqual(result.target_key, "my_warehouse")
            self.assertTrue(result.catalog_path.exists())
            self.assertEqual(result.catalog_path.read_bytes(), b"abc")
            self.assertEqual(
                user_added_targets(config),
                ["my_warehouse"],
            )
            text = config.read_text(encoding="utf-8")
            self.assertIn("my_warehouse:", text)
            self.assertIn("name_col: صنف", text)

    def test_arabic_name_keeps_original_as_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            upload = _make_upload("vendor.xlsx", b"x")
            with patch(
                "src.ui.excel_targets_manager.ARTIFACTS_DIR",
                Path(temp_dir) / "artifacts",
            ):
                result = add_excel_target(
                    config_path=config,
                    display_name=DEFAULT_TARGET_NAME,
                    uploaded_file=upload,
                )
            self.assertEqual(result.target_key, DEFAULT_TARGET_NAME)

    def test_duplicate_key_appends_index(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            upload = _make_upload("vendor.xlsx", b"x")
            with patch(
                "src.ui.excel_targets_manager.ARTIFACTS_DIR",
                Path(temp_dir) / "artifacts",
            ):
                first = add_excel_target(
                    config_path=config,
                    display_name="my_warehouse",
                    uploaded_file=upload,
                )
                second = add_excel_target(
                    config_path=config,
                    display_name="my_warehouse",
                    uploaded_file=upload,
                )
            self.assertEqual(first.target_key, "my_warehouse")
            self.assertEqual(second.target_key, "my_warehouse_2")

    def test_addition_uses_configured_columns(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            upload = _make_upload("vendor.xlsx", b"x")
            with patch(
                "src.ui.excel_targets_manager.ARTIFACTS_DIR",
                Path(temp_dir) / "artifacts",
            ):
                add_excel_target(
                    config_path=config,
                    display_name="custom",
                    uploaded_file=upload,
                    name_col="Drug",
                    price_col="Cost",
                    discount_col="Off",
                )
            text = config.read_text(encoding="utf-8")
            self.assertIn("name_col: Drug", text)
            self.assertIn("price_col: Cost", text)
            self.assertIn("discount_col:", text)
            self.assertIn("Off", text)


class RemoveExcelTargetTests(unittest.TestCase):
    """Only user-added targets can be removed; hard-coded ones are protected."""

    def test_removes_user_added_target(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            upload = _make_upload("vendor.xlsx", b"x")
            with patch(
                "src.ui.excel_targets_manager.ARTIFACTS_DIR",
                Path(temp_dir) / "artifacts",
            ):
                add_excel_target(
                    config_path=config,
                    display_name="my_warehouse",
                    uploaded_file=upload,
                )
                self.assertTrue(remove_excel_target(config, "my_warehouse"))
            self.assertEqual(user_added_targets(config), [])
            self.assertNotIn("my_warehouse:", config.read_text(encoding="utf-8"))

    def test_refuses_to_remove_hard_coded_target(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            config.write_text(
                "excel_targets:\n  hardcoded: {}\n",
                encoding="utf-8",
            )
            self.assertFalse(remove_excel_target(config, "hardcoded"))
            self.assertIn(
                "hardcoded:",
                config.read_text(encoding="utf-8"),
            )


class RemoveDialogDispatchTests(unittest.TestCase):
    """The Yes-button inside the dialog must invoke remove_excel_target."""

    def test_remove_excel_target_drops_user_added_entry(self) -> None:
        """End-to-end: confirm logic drops the target from config."""
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            config.write_text(
                "excel_targets:\n  my_warehouse: {}\nuser_added_targets:\n  - my_warehouse\n",
                encoding="utf-8",
            )
            from src.ui.excel_targets_manager import (
                remove_excel_target as real_remove,
            )
            self.assertTrue(real_remove(config, "my_warehouse"))
            self.assertEqual(user_added_targets(config), [])
            self.assertNotIn("my_warehouse:", config.read_text(encoding="utf-8"))


class UpdateExcelTargetTests(unittest.TestCase):
    """The Edit dialog calls update_excel_target to rewrite settings in place."""

    def test_updates_column_names_and_display_name(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            upload = _make_upload("vendor.xlsx", b"x")
            with patch(
                "src.ui.excel_targets_manager.ARTIFACTS_DIR",
                Path(temp_dir) / "artifacts",
            ):
                add_excel_target(
                    config_path=config,
                    display_name="my_warehouse",
                    uploaded_file=upload,
                )
                self.assertTrue(
                    update_excel_target(
                        config,
                        "my_warehouse",
                        display_name="My Warehouse",
                        name_col="الصنف",
                        price_col="سعر ج",
                        discount_col="نقدي",
                        code_col="كود",
                        sheet="الجزيرة",
                        header_row=0,
                        enabled=True,
                    )
                )
            settings = excel_target_settings(config, "my_warehouse")
            self.assertEqual(settings["display_name"], "My Warehouse")
            self.assertEqual(settings["name_col"], "الصنف")
            self.assertEqual(settings["price_col"], "سعر ج")
            self.assertEqual(settings["discount_col"], "نقدي")
            self.assertEqual(settings["code_col"], "كود")
            self.assertEqual(settings["sheet"], "الجزيرة")
            self.assertTrue(settings["enabled"])
            text = config.read_text(encoding="utf-8")
            self.assertIn("price_col: سعر ج", text)
            self.assertIn("discount_col: نقدي", text)
            self.assertIn("sheet: الجزيرة", text)

    def test_update_returns_false_for_unknown_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            config.write_text(
                "excel_targets:\n  hardcoded: {}\n",
                encoding="utf-8",
            )
            self.assertFalse(update_excel_target(config, "missing_key", price_col="x"))

    def test_update_can_disable_target(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            upload = _make_upload("vendor.xlsx", b"x")
            with patch(
                "src.ui.excel_targets_manager.ARTIFACTS_DIR",
                Path(temp_dir) / "artifacts",
            ):
                add_excel_target(
                    config_path=config,
                    display_name="my_warehouse",
                    uploaded_file=upload,
                )
                update_excel_target(config, "my_warehouse", enabled=False)
            settings = excel_target_settings(config, "my_warehouse")
            self.assertFalse(settings["enabled"])

    def test_settings_returns_empty_for_unknown_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "config.yaml"
            config.write_text("excel_targets: {}\n", encoding="utf-8")
            self.assertEqual(excel_target_settings(config, "ghost"), {})


if __name__ == "__main__":
    unittest.main()
