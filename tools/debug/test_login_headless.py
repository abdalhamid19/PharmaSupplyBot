#!/usr/bin/env python3
"""Quick test of login with corrected selectors - saves result to file."""

from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("TAWREED_EMAIL", "").strip()
password = os.getenv("TAWREED_PASSWORD", "").strip()

result = []
result.append(f"Email: {email}")
result.append(f"Password: {'*' * len(password)}\n")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=0)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(45000)
        
        result.append("1. Opening login page...")
        page.goto("https://seller.tawreed.io/#/login", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        result.append("2. Filling username...")
        page.locator("input[name='username'], input#username").first.fill(email)
        
        result.append("3. Filling password...")
        page.locator("input[type='password']").first.fill(password)
        
        result.append("4. Clicking submit...")
        page.locator("button[type='submit']").first.click()
        
        result.append("5. Waiting for navigation...")
        page.wait_for_timeout(5000)
        
        # Check if logged in
        url = page.url
        result.append(f"\nCurrent URL: {url}")
        
        if "login" not in url:
            result.append("✅ SUCCESS - Login worked! Not on login page anymore.")
        else:
            result.append("❌ FAILED - Still on login page.")
            page.screenshot(path="login_failed.png")
        
        browser.close()
        
except Exception as e:
    result.append(f"\n❌ ERROR: {str(e)}")

# Save result
with open("login_test_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(result))

print("\n".join(result))
