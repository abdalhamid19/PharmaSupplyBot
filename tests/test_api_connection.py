#!/usr/bin/env python3
"""اختبار سريع للتحقق من عمل Tawreed API"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from src.tawreed.api.tawreed_api_client import TawreedApiClient
from src.core.utils.excel import Item

def test_api_search():
    """اختبار بحث API عن صنف"""
    state_path = Path("state/wardany.json")
    base_url = "https://seller.tawreed.io"
    
    if not state_path.exists():
        print(f"[X] State file missing: {state_path}")
        return False
    
    print(f"[OK] State file found: {state_path}")
    
    try:
        # إنشاء API client
        api = TawreedApiClient(base_url, state_path)
        print(f"[OK] API client created")
        
        # فحص العقد المتاح
        contract = api.contract
        print(f"\n[Contract Available]:")
        print(f"  - product_search_url: {'YES' if contract.product_search_url else 'NO'}")
        print(f"  - add_to_cart_url: {'YES' if contract.add_to_cart_url else 'NO'}")
        print(f"  - remove_cart_url: {'YES' if contract.remove_cart_url else 'NO'}")
        print(f"  - submit_order_url: {'YES' if contract.submit_order_url else 'NO'}")
        
        # اختبار البحث عن صنف
        test_item = "Panadol"
        print(f"\n[Search Test]: {test_item}")
        
        results = api.search_products(test_item)
        print(f"[OK] Search results: {len(results)} items")
        
        if results:
            first = results[0]
            print(f"\n[First Result]:")
            print(f"  - productName: {first.get('productName', 'N/A')}")
            print(f"  - productNameEn: {first.get('productNameEn', 'N/A')}")
            print(f"  - storeProductId: {first.get('storeProductId', 'N/A')}")
            print(f"  - storeName: {first.get('storeName', 'N/A')}")
            print(f"  - availableQuantity: {first.get('availableQuantity', 'N/A')}")
            print(f"  - salePrice: {first.get('salePrice', 'N/A')}")
        
        print(f"\n[SUCCESS] API is working!")
        return True
        
    except Exception as error:
        print(f"\n[ERROR] API failed: {error}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_search()
    exit(0 if success else 1)
