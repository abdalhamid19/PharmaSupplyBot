"""Navigate to the Order tab and inspect the Excel target upload widgets."""

from playwright.sync_api import sync_playwright

URL = "http://localhost:8765"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    # Click the "Order" nav item in the sidebar
    order_nav = page.get_by_text("Order", exact=True).first
    order_nav.click()
    page.wait_for_timeout(4000)

    body_text = page.inner_text("body")
    out = open("tools/debug/order_tab_text.txt", "w", encoding="utf-8")
    out.write(body_text)
    out.close()
    print("=== BODY TEXT (first 4000 chars) ===")
    print(body_text[:4000].encode("ascii", "replace").decode())

    print("\n=== SEARCHING FOR KEY LABELS ===")
    for label in [
        "Run Order",
        "Run target",
        "Excel target source",
        "Excel source",
        "Upload Excel",
        "Upload catalog",
        "Configured",
        "Existing file",
        "Upload file",
        "alnasr",
        "Excel target",
        "Tawreed profile",
    ]:
        found = label.lower() in body_text.lower()
        print(f"  {'FOUND' if found else 'MISSING'}: {label!r}")

    print("\n=== EXCEPTION CHECK ===")
    for marker in ["Exception", "Traceback", "error"]:
        if marker in body_text:
            idx = body_text.find(marker)
            print(f"  marker {marker!r}: {body_text[max(0,idx-200):idx+400]}".encode("ascii", "replace").decode())
        else:
            print(f"  clean: no {marker!r}")

    page.screenshot(path="gui_order_tab.png", full_page=True)
    browser.close()