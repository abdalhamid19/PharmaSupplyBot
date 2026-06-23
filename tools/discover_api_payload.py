#!/usr/bin/env python3
"""
Interactive script to discover correct API payload structure.

Usage:
    python3 tools/discover_api_payload.py --profile wardany
    
This script will:
1. Open browser with network capture enabled
2. Wait for you to manually add ONE item to cart
3. Capture and analyze the request
4. Save the correct payload structure
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config.config import load_config
from src.tawreed.tawreed_api_discovery_enhanced import (
    begin_detailed_api_capture,
    save_captured_requests,
    analyze_add_to_cart_payload,
)
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(
        description="Discover correct API payload structure by capturing browser requests"
    )
    parser.add_argument("--profile", required=True, help="Profile name (e.g., wardany)")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    
    args = parser.parse_args()
    
    # Load config
    app_config = load_config(Path(args.config))
    profile = app_config.profiles.get(args.profile)
    if not profile:
        print(f"❌ Profile '{args.profile}' not found in config")
        return 1
    
    state_path = Path("state") / f"{args.profile}.json"
    if not state_path.exists():
        print(f"❌ State file not found: {state_path}")
        print(f"   Run: python3 run.py auth --profile {args.profile}")
        return 1
    
    print("=" * 70)
    print("🔍 API Payload Discovery Tool")
    print("=" * 70)
    print()
    print("📋 Instructions:")
    print("1. A browser window will open with Tawreed")
    print("2. Manually navigate to products page")
    print("3. Add ONE item to cart (any item)")
    print("4. Wait 2 seconds after adding")
    print("5. Close the browser or press Ctrl+C")
    print()
    print("⏳ The tool will capture and analyze the request automatically")
    print()
    input("Press ENTER to start...")
    
    # Start browser with capture
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(state_path),
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        # Start capture
        captured = begin_detailed_api_capture(page)
        
        print(f"\n✅ Network capture started")
        print(f"🌐 Opening Tawreed...")
        
        # Navigate to Tawreed
        page.goto(app_config.base_url, wait_until="domcontentloaded")
        
        print(f"\n📝 Browser is ready!")
        print(f"   👉 Add ONE item to cart, then close browser")
        
        try:
            # Wait for user to close browser
            page.wait_for_timeout(300000)  # 5 minutes max
        except Exception:
            pass
        
        finally:
            print(f"\n📊 Analyzing {len(captured)} captured requests...")
            
            # Save captured requests
            capture_file = save_captured_requests(
                captured, 
                args.profile,
                "add_to_cart_discovery"
            )
            
            # Analyze
            analysis = analyze_add_to_cart_payload(capture_file)
            
            print("\n" + "=" * 70)
            print("📊 Analysis Results")
            print("=" * 70)
            
            if "error" in analysis:
                print(f"\n❌ {analysis['error']}")
                print(f"   Make sure you added an item to cart!")
            else:
                print(f"\n✅ Found {analysis['total_requests']} add-to-cart requests")
                print(f"\n🔗 URLs:")
                for url in analysis["urls"]:
                    print(f"   • {url}")
                
                print(f"\n📦 Sample Payload:")
                import json
                print(json.dumps(analysis["sample_payload"], indent=2, ensure_ascii=False))
                
                print(f"\n🏷️  Payload Fields:")
                for field in analysis["payload_fields"]["all_fields"]:
                    field_type = analysis["payload_fields"]["field_types"].get(field, "unknown")
                    print(f"   • {field}: {field_type}")
                
                print(f"\n📄 Full capture saved to:")
                print(f"   {capture_file}")
            
            browser.close()
    
    print("\n✅ Discovery completed!")
    print("\n💡 Next steps:")
    print("   1. Review the payload structure above")
    print("   2. Update body_with_match() in src/tawreed/tawreed_api_payloads.py")
    print("   3. Test with: python3 run.py order --limit 1 --profile wardany")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
