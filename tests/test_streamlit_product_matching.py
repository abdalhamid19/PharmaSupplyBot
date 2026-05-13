import unittest
from pathlib import Path

from src.ui.streamlit_product_matching import product_matching_command


class StreamlitProductMatchingTests(unittest.TestCase):
    def test_product_matching_command_includes_cli_options(self) -> None:
        command = product_matching_command(
            Path("config.yaml"),
            {
                "profile_key": "wardany",
                "limit": 5,
                "trace": True,
                "no_ai": True,
                "provider": "rotation",
                "model": "",
                "review_model": "rotation",
                "concurrency": 4,
            },
            Path("data/input/order_items/items.xlsx"),
            Path("artifacts/wardany/product_matching.csv"),
        )

        self.assertIn("match-products", command)
        self.assertIn("--trace", command)
        self.assertIn("--no-ai", command)
        self.assertIn("rotation", command)


if __name__ == "__main__":
    unittest.main()
