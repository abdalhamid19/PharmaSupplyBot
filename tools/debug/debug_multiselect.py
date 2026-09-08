"""Dump the multiselect dropdown DOM to debug why the option isn't visible."""

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
    proc = subprocess.Popen(
        [
            ".venv/Scripts/python.exe",
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.port",
            "8771",
            "--server.headless",
            "true",
        ],
        cwd=str(Path(__file__).parent.parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_for_server("http://localhost:8771")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8771", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # Switch sidebar config to the real one with excel_targets if needed
            sidebar = page.locator('[data-testid="stSidebar"]').inner_text()
            print("sidebar text snippet:", sidebar[:300].encode("ascii", "replace").decode())

            page.get_by_text("Order", exact=True).first.click()
            page.wait_for_timeout(3000)

            # Find all multiselect containers
            mses = page.locator('[data-testid="stMultiSelect"]').all()
            print(f"\nfound {len(mses)} multiselect containers")
            for i, m in enumerate(mses):
                txt = m.inner_text()
                print(f"  [{i}] text: {txt!r}")
                # Inspect dropdown panel if open
                opts = m.locator('li[role="option"]').all()
                print(f"    dropdown options ({len(opts)}):")
                for o in opts:
                    print(f"      - {o.inner_text()!r}")

            # Try opening the first multiselect by clicking the inner input
            print("\n=== Trying to open multiselect[0] ===")
            ms0 = mses[0]
            ms0.scroll_into_view_if_needed()
            ms0.click()
            page.wait_for_timeout(1500)
            opts = ms0.locator('li[role="option"]').all()
            print(f"  options visible after click: {len(opts)}")
            for o in opts:
                print(f"    - {o.inner_text()!r}")

            # Inspect the Run target multiselect labels more deeply
            labels = page.locator('[data-testid="stWidgetLabel"]').all()
            for lbl in labels:
                print(f"  label: {lbl.inner_text()!r}")

            page.screenshot(path="tools/debug/live_dom.png", full_page=True)
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