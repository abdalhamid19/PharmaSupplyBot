"""Drive the live Streamlit app: switch to Order tab, pick alnasr, verify upload widgets."""

from playwright.sync_api import sync_playwright

URL = "http://localhost:8765"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    # Step 1: sidebar shows the loaded config path. Check what config is loaded.
    body0 = page.inner_text("body")
    print("=== Initial state ===")
    for line in body0.splitlines():
        if "Loaded config" in line or "Config path" in line:
            print(" ", line)

    # Look for the Order nav button in the sidebar
    page.get_by_text("Order", exact=True).first.click()
    page.wait_for_timeout(4000)
    body1 = page.inner_text("body")
    print("\n=== After Order click ===")
    print("Run Order found:", "Run Order" in body1)
    print("Run target found:", "Run target" in body1)
    # Check Excel target option text
    excel_options = [
        o for o in body1.split("\n") if "Excel target" in o
    ]
    print("Excel target options:", excel_options)

    # Open Run target multiselect — find a label "Run target" and click the open icon next to it
    # Simpler: find the multiselect container and click it
    ms = page.locator('[data-testid="stMultiSelect"]').first
    if ms.count() == 0:
        print("FAIL: no multiselect found")
        page.screenshot(path="debug_no_ms.png")
        browser.close()
        raise SystemExit(1)
    ms.click()
    page.wait_for_timeout(2000)

    # Look for the alnasr option in the dropdown panel
    alnasr_panel = page.locator('li[role="option"]').filter(has_text="Excel target — alnasr").first
    alnasr_count = page.locator('li[role="option"]').filter(has_text="Excel target").count()
    print(f"alnasr option count: {alnasr_count}")
    if alnasr_count == 0:
        print("Dropdown options containing 'Excel target':",
              [o.inner_text() for o in page.locator('li[role="option"]').all()])
        page.screenshot(path="debug_dropdown.png")
        browser.close()
        raise SystemExit(1)
    alnasr_panel.click()
    page.wait_for_timeout(2000)

    # Close the dropdown by clicking elsewhere
    page.locator("body").click(position={"x": 1, "y": 1})
    page.wait_for_timeout(2000)

    # Now check for the upload widget block
    body2 = page.inner_text("body")
    print("\n=== After selecting alnasr ===")
    print("'Excel target source' present:", "Excel target source" in body2)
    print("'Source for' present:", "Source for" in body2)
    print("'Configured' present:", "Configured" in body2)
    print("'Existing file' present:", "Existing file" in body2)
    print("'Upload file' present:", "Upload file" in body2)
    print("'Upload catalog' present:", "Upload catalog" in body2)
    print("Exception markers:", [m for m in ("Exception", "AttributeError") if m in body2])

    page.screenshot(path="debug_after_select.png", full_page=True)
    browser.close()