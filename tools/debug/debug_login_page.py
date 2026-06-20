#!/usr/bin/env python3
"""Debug script to inspect Tawreed login page structure."""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    print("Opening: https://seller.tawreed.io/#/login")
    page.goto("https://seller.tawreed.io/#/login", wait_until="domcontentloaded")
    
    # Wait a bit for any dynamic content
    time.sleep(3)
    
    # Save page content
    html = page.content()
    with open("login_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✓ Saved page HTML to: login_page.html")
    
    # Take screenshot
    page.screenshot(path="login_page.png")
    print("✓ Saved screenshot to: login_page.png")
    
    # Try to find email inputs
    print("\n=== Checking for email inputs ===")
    email_selectors = [
        "input[type='email']",
        "input[name='email']",
        "input[type='email'], input[name='email']",
        "input[placeholder*='email' i]",
        "input[placeholder*='بريد' i]",
        "input"
    ]
    
    for selector in email_selectors:
        try:
            count = page.locator(selector).count()
            print(f"{selector:50} -> {count} matches")
            if count > 0:
                for i in range(count):
                    elem = page.locator(selector).nth(i)
                    attrs = page.evaluate("""
                        (el) => {
                            return {
                                tag: el.tagName,
                                type: el.type,
                                name: el.name,
                                id: el.id,
                                class: el.className,
                                placeholder: el.placeholder
                            };
                        }
                    """, elem.element_handle())
                    print(f"  [{i}] {attrs}")
        except Exception as e:
            print(f"{selector:50} -> Error: {e}")
    
    print("\n=== Press Enter to close ===")
    input()
    
    browser.close()
