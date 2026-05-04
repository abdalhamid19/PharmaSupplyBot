import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.ui.streamlit_process import cli_command, output_stream
from src.ui.streamlit_subprocess_env import merged_env


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

    def test_cli_command_uses_project_runner(self) -> None:
        command = cli_command(["order", "--profile", "wardany"])

        self.assertEqual(command[2:], ["order", "--profile", "wardany"])
        self.assertTrue(command[1].endswith("run.py"))

    def test_output_stream_creates_parent_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "command.log"

            output_file = output_stream(output_path)
            output_file.write("ok")
            output_file.close()

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_text(encoding="utf-8"), "ok")


if __name__ == "__main__":
    unittest.main()
