#!/usr/bin/env python3
"""Quick test of login with corrected selectors."""

from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("TAWREED_EMAIL", "").strip()
password = os.getenv("TAWREED_PASSWORD", "").strip()

print(f"Email: {email}")
print(f"Password: {'*' * len(password)}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(45000)
    
    print("\n1. Opening login page...")
    page.goto("https://seller.tawreed.io/#/login", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    
    print("2. Filling username...")
    page.locator("input[name='username'], input#username").first.fill(email)
    
    print("3. Filling password...")
    page.locator("input[type='password']").first.fill(password)
    
    print("4. Clicking submit...")
    page.locator("button[type='submit']").first.click()
    
    print("5. Waiting for navigation...")
    page.wait_for_timeout(5000)
    
    # Check if logged in
    url = page.url
    print(f"\nCurrent URL: {url}")
    
    if "login" not in url:
        print("✅ SUCCESS - Login worked! Not on login page anymore.")
    else:
        print("❌ FAILED - Still on login page.")
        page.screenshot(path="login_failed.png")
    
    input("\nPress Enter to close...")
    browser.close()
