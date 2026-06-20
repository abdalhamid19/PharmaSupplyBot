#!/usr/bin/env python3
"""Test login with proper form interactions."""

from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("TAWREED_EMAIL", "").strip()
password = os.getenv("TAWREED_PASSWORD", "").strip()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(45000)
    
    print("1. Opening login page...")
    page.goto("https://seller.tawreed.io/#/login", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    
    print("2. Filling username...")
    username_input = page.locator("input[name='username']#username")
    username_input.click()
    username_input.fill(email)
    username_input.press("Tab")  # Trigger validation
    page.wait_for_timeout(500)
    
    print("3. Filling password...")
    password_input = page.locator("input[type='password'][name='password']")
    password_input.click()
    password_input.fill(password)
    page.wait_for_timeout(500)
    
    print("4. Checking button state...")
    button = page.locator("button.p-button:has-text('دخول')")
    is_disabled = button.get_attribute("disabled")
    print(f"   Button disabled: {is_disabled}")
    
    if is_disabled:
        print("5. Waiting for button to enable...")
        page.wait_for_selector("button.p-button:has-text('دخول'):not([disabled])", timeout=5000)
    
    print("6. Clicking submit...")
    button.click()
    
    print("7. Waiting for navigation...")
    page.wait_for_timeout(5000)
    
    url = page.url
    print(f"\nFinal URL: {url}")
    
    if "login" not in url:
        print("✅ SUCCESS")
    else:
        print("❌ FAILED")
        page.screenshot(path="login_failed.png")
    
    browser.close()
