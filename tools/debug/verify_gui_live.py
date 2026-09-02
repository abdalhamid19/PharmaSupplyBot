"""Live verify the redesigned checkbox-based Excel target source panel."""

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
    import subprocess

    proc = subprocess.Popen(
        [
            ".venv/Scripts/python.exe",
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.port",
            "8774",
            "--server.headless",
            "true",
        ],
        cwd=str(Path(__file__).parent.parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_server("http://localhost:8774"):
            print("FAIL: server did not start")
            return 1
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8774", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            page.get_by_text("Order", exact=True).first.click()
            page.wait_for_timeout(3000)

            body = page.inner_text("body")
            print("=== After clicking Order tab ===")
            print(f"  'What to run against?' present: {'What to run against?' in body}")
            print(f"  'Tawreed profile' present: {'Tawreed profile' in body}")
            print(f"  'Excel target' present: {'Excel target' in body}")
            print(f"  'alnasr' present: {'alnasr' in body}")
            print(f"  'Excel target source' present (initially): {'Excel target source' in body}")

            # Find the alnasr checkbox by its label
            alnasr_label = page.locator('label').filter(has_text="Excel target (alnasr)").first
            alnasr_count = page.locator('label').filter(has_text="alnasr").count()
            print(f"  alnasr checkbox labels found: {alnasr_count}")
            if alnasr_count == 0:
                page.screenshot(path="tools/debug/live_no_alnasr.png", full_page=True)
                browser.close()
                return 1

            # Find the checkbox by its exact label and click it via the input element
            checkbox_inputs = page.locator('input[type="checkbox"]').all()
            print(f"  total checkbox inputs: {len(checkbox_inputs)}")
            # The first profile checkbox is at index 0 (default checked),
            # alnasr is at index 1 in our setup
            for i, cb in enumerate(checkbox_inputs):
                # Walk up two levels to find the label text
                parent = cb.locator('xpath=..')
                grandparent = parent.locator('xpath=..')
                txt = (grandparent.inner_text() or "").strip()
                if "alnasr" in txt:
                    print(f"  found alnasr checkbox at index {i}")
                    cb.check(force=True, timeout=5000)
                    break
            page.wait_for_timeout(4000)

            body_after = page.inner_text("body")
            print("\n=== After clicking alnasr checkbox ===")
            print(f"  'Excel target source' present: {'Excel target source' in body_after}")
            print(f"  'Source' radio present: {'Source' in body_after}")
            print(f"  'Configured' present: {'Configured' in body_after}")
            print(f"  'Existing file' present: {'Existing file' in body_after}")
            print(f"  'Upload file' present: {'Upload file' in body_after}")
            page.screenshot(path="tools/debug/live_after_check.png", full_page=True)

            # Click the Upload file radio
            radios_now = page.locator('input[type="radio"]').all()
            print(f"  total radio inputs: {len(radios_now)}")
            upload_label_count = page.locator('label').filter(has_text="Upload file").count()
            print(f"  'Upload file' labels found: {upload_label_count}")
            if upload_label_count >= 2:
                # The second one is in our panel
                page.locator('label').filter(has_text="Upload file").nth(upload_label_count - 1).click(force=True, timeout=5000)
                page.wait_for_timeout(3000)

            body_final = page.inner_text("body")
            print("\n=== After clicking Upload file ===")
            print(f"  'Upload catalog' present: {'Upload catalog' in body_final}")
            print(f"  'Browse files' present: {'Browse files' in body_final}")
            print(f"  'Drag and drop' present: {'Drag and drop' in body_final}")

            page.screenshot(path="tools/debug/live_redesign.png", full_page=True)
            browser.close()

            ok = (
                "Excel target source" in body_after
                and "Upload catalog" in body_final
            )
            print(f"\n{'ALL WIDGETS VISIBLE' if ok else 'FAIL: widgets not visible'}")
            return 0 if ok else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())