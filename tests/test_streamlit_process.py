import os
import unittest
from unittest.mock import patch

from src.streamlit_subprocess_env import merged_env


class StreamlitProcessTests(unittest.TestCase):
    def test_merged_env_applies_non_empty_overrides(self) -> None:
        with patch.dict(os.environ, {"EMPTY": "keep-me"}, clear=False):
            env = merged_env({"TAWREED_EMAIL": "user@example.com", "EMPTY": ""})
        self.assertEqual(env["TAWREED_EMAIL"], "user@example.com")
        self.assertEqual(env["EMPTY"], "keep-me")

    def test_merged_env_preserves_existing_environment(self) -> None:
        original = os.environ.get("PATH", "")
        env = merged_env(None)
        self.assertEqual(env.get("PATH", ""), original)


if __name__ == "__main__":
    unittest.main()
