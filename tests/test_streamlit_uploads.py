import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.ui.streamlit_uploads import available_excel_options


class StreamlitUploadsTests(unittest.TestCase):
    def test_available_excel_options_reads_order_items_directory_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            order_dir = root / "order_items"
            prevented_dir = root / "prevented_items"
            order_dir.mkdir()
            prevented_dir.mkdir()
            (order_dir / "orders.xlsx").write_bytes(b"")
            (prevented_dir / "drugprevented.xlsx").write_bytes(b"")

            with patch("src.ui.streamlit_uploads.ORDER_ITEMS_DIR", order_dir):
                options = available_excel_options()

        self.assertEqual(options, [str(order_dir / "orders.xlsx")])


if __name__ == "__main__":
    unittest.main()
