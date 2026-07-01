import unittest
from pathlib import Path
from unittest.mock import patch

from src.ui.streamlit_shared import DEFAULT_CONFIG_PATH, FALLBACK_CONFIG_PATH, resolved_streamlit_config_path


class StreamlitSharedTests(unittest.TestCase):
    def test_resolved_streamlit_config_path_uses_existing_selected_path(self) -> None:
        with patch.object(Path, "exists", autospec=True) as exists:
            exists.side_effect = lambda path: path == DEFAULT_CONFIG_PATH
            self.assertEqual(resolved_streamlit_config_path(DEFAULT_CONFIG_PATH), DEFAULT_CONFIG_PATH)

    def test_resolved_streamlit_config_path_falls_back_for_missing_default(self) -> None:
        with patch.object(Path, "exists", autospec=True) as exists:
            exists.side_effect = lambda path: path == FALLBACK_CONFIG_PATH
            self.assertEqual(resolved_streamlit_config_path(DEFAULT_CONFIG_PATH), FALLBACK_CONFIG_PATH)

    def test_resolved_streamlit_config_path_keeps_custom_missing_path(self) -> None:
        custom_path = Path("missing-custom.yaml")
        with patch.object(Path, "exists", autospec=True, return_value=False):
            self.assertEqual(resolved_streamlit_config_path(custom_path), custom_path)


if __name__ == "__main__":
    unittest.main()
