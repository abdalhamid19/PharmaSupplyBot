"""
اختبار استرجاع تصحيح AVIL 6 AMP من CockroachDB
"""
from src.core.manual_review_store import ManualReviewStore
from src.core.manual_review_hints import hint_key
from src.core.utils.excel import Item

print("=== Testing AVIL 6 AMP Manual Review Lookup ===\n")

# الاتصال بـ CockroachDB
print("1. Connecting to CockroachDB...")
try:
    store = ManualReviewStore()
    print("   OK - Connected\n")
except Exception as e:
    print(f"   ERROR: {e}\n")
    exit(1)

# البحث عن التصحيح
item_code = "73396"
item_name = "AVIL 6 AMP"

print(f"2. Looking up: {item_code} | {item_name}")
code_key, name_key = hint_key(item_code, item_name)
print(f"   Normalized keys: code='{code_key}' name='{name_key}'\n")

try:
    decision = store.lookup(item_code, item_name)
    
    if decision:
        print("   ✓ FOUND in CockroachDB!")
        print(f"\n   Decision Details:")
        print(f"   - Item Code: {decision.item_code}")
        print(f"   - Item Name: {decision.item_name}")
        print(f"   - Approved: {decision.approved}")
        print(f"   - Manual Decision: {decision.manual_decision}")
        print(f"   - Store Product ID: {decision.correct_store_product_id}")
        print(f"   - Product Name EN: {decision.correct_product_name}")
        print(f"   - Product Name AR: {decision.correct_product_name_ar}")
        print(f"   - Correct Query: {decision.correct_query}")
        print(f"   - Run ID: {decision.run_id}")
    else:
        print("   ✗ NOT FOUND in CockroachDB")
        print("   The correction does not exist in the database")
        
except Exception as e:
    print(f"   ERROR during lookup: {e}")
    import traceback
    traceback.print_exc()

# اختبار مع Item object
print("\n3. Testing with Item object...")
try:
    from src.core.manual_review_runtime import saved_manual_review_decision
    
    item = Item(code=item_code, name=item_name, qty=1)
    decision = saved_manual_review_decision(item)
    
    if decision:
        print("   ✓ saved_manual_review_decision() works!")
        print(f"   - Approved: {decision.approved}")
        print(f"   - Store Product ID: {decision.correct_store_product_id}")
    else:
        print("   ✗ saved_manual_review_decision() returned None")
        
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

# اختبار manual_review_match
print("\n4. Testing manual_review_match logic...")
try:
    from src.core.manual_review_runtime import manual_review_match
    
    # محاكاة نتائج بحث تحتوي على المنتج الصحيح
    mock_results = [
        ("AVIL 6 AMP", [
            {
                "storeProductId": "2640615",
                "productNameEn": "AVIL 45.5 MG / 2 ML 6 I.M. AMPS.",
                "productName": "افيل 45.5 مجم / 2 مل 6 امبول",
                "availableQuantity": 147
            },
            {
                "storeProductId": "2497017",
                "productNameEn": "AVILAC 10 SACHETS",
                "productName": "افيلاك 10 اكياس",
                "availableQuantity": 3
            }
        ])
    ]
    
    item = Item(code=item_code, name=item_name, qty=1)
    match_decision = manual_review_match(item, mock_results, decision)
    
    if match_decision:
        print("   ✓ manual_review_match() found forced match!")
        print(f"   - Query: {match_decision.best_match.query}")
        print(f"   - Score: {match_decision.best_match.score}")
        print(f"   - Reason: {match_decision.reason}")
        print(f"   - Store Product ID: {match_decision.best_match.candidate.get('storeProductId')}")
    else:
        print("   ✗ manual_review_match() returned None")
        print("   This means the correction is NOT being applied!")
        
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
