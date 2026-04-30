import unittest
from pathlib import Path

from src.streamlit_order import order_command


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

        self.assertEqual(command[-2:], ["--warehouse-mode", "max_discount"])


if __name__ == "__main__":
    unittest.main()
