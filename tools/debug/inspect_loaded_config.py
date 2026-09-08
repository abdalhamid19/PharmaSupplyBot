"""Debug: log what load_config actually returns when the live server runs it."""

import subprocess
import time
from pathlib import Path


def wait_for_server(url: str, timeout: float = 30) -> bool:
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2).read()
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    return False


def main() -> int:
    proc = subprocess.Popen(
        [
            ".venv/Scripts/python.exe",
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.port",
            "8773",
            "--server.headless",
            "true",
        ],
        cwd=str(Path(__file__).parent.parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_server("http://localhost:8773")
        # Read what the server prints
        time.sleep(2)
        import requests

        r = requests.get("http://localhost:8773/_stcore/health", timeout=5)
        print("health:", r.status_code, r.text[:100])

        # Use the streamlit script-runner endpoint to evaluate a python expression
        # via the streamlit websocket API
        # Simpler: spawn a subprocess that loads the same way
        result = subprocess.run(
            [".venv/Scripts/python.exe", "-c", """
from pathlib import Path
import sys
sys.path.insert(0, '.')
from src.core.config.config import load_config
cfg = load_config(Path('state/config.yaml'))
print('profiles:', list(cfg.profiles.keys()))
print('excel_targets:', list(cfg.excel_targets.keys()))
print('enabled:', list(cfg.enabled_excel_targets().keys()))
for key, t in cfg.excel_targets.items():
    print(f'  {key}: name_col={t.name_col!r} price_col={t.price_col!r} discount_col={t.discount_col!r} display_name={t.display_name!r} enabled={t.enabled}')
"""],
            capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent),
        )
        print("config load result:")
        print(result.stdout)
        print("stderr:", result.stderr)
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())