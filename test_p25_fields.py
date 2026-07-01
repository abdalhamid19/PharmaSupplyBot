"""Test P2.5 fields reorganization - simplified test to verify imports work."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

# Test the updated imports after P2.5
from src.ui.fields.streamlit_excel_fields import order_excel_options
from src.ui.order.streamlit_order import DEFAULT_PREVENTED_ITEMS_PATH
from src.ui.order.streamlit_order import order_command

class TestP25FieldsReorganization(unittest.TestCase):
    """Test that P2.5 fields reorganization works correctly."""

    def test_order_excel_options_excludes_default_prevented_items_file(self) -> None:
        """Test that the patch path for excel_options works after reorganization."""
        with patch(
            "src.ui.fields.streamlit_excel_fields.available_excel_options",
            return_value=[
                "data/input/order_items/shortage_report_total_20260426.xlsx",
            ],
        ):
            options = order_excel_options()

        self.assertEqual(
            options, ["data/input/order_items/shortage_report_total_20260426.xlsx"]
        )

    def test_order_command_basic(self) -> None:
        """Test that order_command import works from new location."""
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

    def test_default_prevented_items_path_import(self) -> None:
        """Test that DEFAULT_PREVENTED_ITEMS_PATH imports correctly."""
        self.assertIsNotNone(DEFAULT_PREVENTED_ITEMS_PATH)
        self.assertIsInstance(DEFAULT_PREVENTED_ITEMS_PATH, Path)

if __name__ == "__main__":
    unittest.main()
