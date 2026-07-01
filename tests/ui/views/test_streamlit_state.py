import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ui import streamlit_default_state
from src.ui import streamlit_state


class FakeUpload:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


class StreamlitStateTests(unittest.TestCase):
    def test_persist_uploaded_state_writes_profile_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(streamlit_state, "STATE_DIR", Path(temp_dir)):
                path = streamlit_state.persist_uploaded_state("wardany", FakeUpload(b'{"ok":true}'))
                self.assertEqual(path.read_bytes(), b'{"ok":true}')

    def test_missing_state_profiles_returns_only_missing_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(streamlit_state, "STATE_DIR", Path(temp_dir)):
                streamlit_state.persist_uploaded_state("wardany", FakeUpload(b"{}"))
                missing = streamlit_state.missing_state_profiles(["wardany", "second"])
                self.assertEqual(missing, ["second"])

    def test_ensure_default_state_file_uses_default_directory_copy(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir:
            with tempfile.TemporaryDirectory() as default_dir:
                with patch.object(streamlit_state, "STATE_DIR", Path(state_dir)):
                    with patch.object(
                        streamlit_default_state,
                        "DEFAULT_STATE_DIR",
                        Path(default_dir),
                    ):
                        default_path = Path(default_dir) / "wardany.json"
                        default_path.write_text('{"cached":true}', encoding="utf-8")
                        path = streamlit_state.ensure_default_state_file("wardany")
                        self.assertIsNotNone(path)
                        self.assertEqual(path.read_text(encoding="utf-8"), '{"cached":true}')


if __name__ == "__main__":
    unittest.main()
