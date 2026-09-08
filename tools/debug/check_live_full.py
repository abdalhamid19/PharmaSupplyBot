"""Force-reload config.yaml by touching it (mtime update) and re-test."""

import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


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
    # Touch the config to ensure it's loaded fresh
    Path("state/config.yaml").touch()

    proc = subprocess.Popen(
        [
            ".venv/Scripts/python.exe",
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.port",
            "8772",
            "--server.headless",
            "true",
        ],
        cwd=str(Path(__file__).parent.parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_server("http://localhost:8772")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8772", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            page.get_by_text("Order", exact=True).first.click()
            page.wait_for_timeout(3000)

            # Look at multiselect container explicitly
            ms = page.locator('[data-testid="stMultiSelect"]').first
            container_html = ms.evaluate("el => el.outerHTML")
            container_text = ms.inner_text()
            print("multiselect text:", container_text.encode("ascii", "replace").decode())
            print("\nmultiselect html (first 2000 chars):")
            print(container_html[:2000])

            # Find the multiselect input
            print("\n=== all multiselect labels ===")
            labels = page.locator('[data-testid="stWidgetLabel"]').all()
            for lbl in labels[:8]:
                print(f"  {lbl.inner_text()!r}")

            # Check if there's an Excel target option in any widget
            body = page.inner_text("body")
            excel_in_body = "Excel target" in body
            alnasr_in_body = "alnasr" in body
            print(f"\nExcel target in body: {excel_in_body}")
            print(f"alnasr in body: {alnasr_in_body}")

            page.screenshot(path="tools/debug/live_check.png", full_page=True)
            browser.close()
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())