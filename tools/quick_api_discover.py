#!/usr/bin/env python3
"""Simple API discovery - captures network for 60 seconds while you add item."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config.config import load_config
from src.tawreed.tawreed_api_discovery_enhanced import (
    begin_detailed_api_capture,
    save_captured_requests,
    analyze_add_to_cart_payload,
)
from playwright.sync_api import sync_playwright
import json

profile = "wardany"
app_config = load_config(Path("config.yaml"))
state_path = Path("state") / f"{profile}.json"

print("🔍 Starting API capture...")
print("📋 Browser will open - add ONE item to cart")
print("⏱️  Will auto-close after 60 seconds\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state=str(state_path))
    page = context.new_page()
    
    captured = begin_detailed_api_capture(page)
    
    page.goto(app_config.base_url, wait_until="domcontentloaded")
    
    print("✅ Browser ready! Add an item now...")
    
    try:
        page.wait_for_timeout(60000)  # 60 seconds
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    
    browser.close()

print(f"\n📊 Captured {len(captured)} requests")

# Save
capture_file = save_captured_requests(captured, profile, "add_to_cart_discovery")

# Analyze
analysis = analyze_add_to_cart_payload(capture_file)

print("\n" + "=" * 70)
if "error" not in analysis:
    print("✅ SUCCESS! Found add-to-cart requests\n")
    print(f"📦 Sample Payload:")
    print(json.dumps(analysis["sample_payload"], indent=2, ensure_ascii=False))
    print(f"\n💾 Full data saved to: {capture_file}")
else:
    print(f"❌ {analysis['error']}")
    print(f"💾 Raw data saved to: {capture_file}")
