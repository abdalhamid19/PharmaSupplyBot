"""Run unit tests with noisy bare Streamlit loggers silenced."""
from __future__ import annotations

import logging
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    """Discover and run repository unit tests."""
    _silence_bare_streamlit_loggers()
    try:
        suite = unittest.defaultTestLoader.discover("tests")
        result = unittest.TextTestRunner(verbosity=0).run(suite)
        return 0 if result.wasSuccessful() else 1
    finally:
        logging.disable(logging.NOTSET)


def _silence_bare_streamlit_loggers() -> None:
    logging.disable(logging.CRITICAL)
    for name in (
        "streamlit",
        "streamlit.runtime.scriptrunner_utils.script_run_context",
        "streamlit.runtime.state.session_state_proxy",
    ):
        logging.getLogger(name).setLevel(logging.ERROR)


if __name__ == "__main__":
    raise SystemExit(main())
