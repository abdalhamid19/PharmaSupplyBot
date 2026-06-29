"""
سكريبت تشخيصي لمشكلة AVIL 6 AMP Manual Review
"""
from src.core.manual_review_store import ManualReviewStore
from src.core.manual_review_runtime import saved_manual_review_decision
from src.core.manual_review_hints import hint_key
from src.core.utils.excel import Item
import time

print("=" * 60)
print("AVIL Manual Review Diagnosis")
print("=" * 60)

# Test 1: Direct store lookup
print("\n1. Direct CockroachDB lookup:")
print("-" * 60)
try:
    store = ManualReviewStore()
    code_key, name_key = hint_key("73396", "AVIL 6 AMP")
    print(f"   Normalized keys:")
    print(f"     code_key  = '{code_key}'")
    print(f"     name_key  = '{name_key}'")
    
    start = time.perf_counter()
    result = store.lookup("73396", "AVIL 6 AMP")
    elapsed = time.perf_counter() - start
    
    if result:
        print(f"\n   ✓ SUCCESS: Found in CockroachDB")
        print(f"     Store Product ID: {result.correct_store_product_id}")
        print(f"     Product Name EN:  {result.correct_product_name}")
        print(f"     Approved:         {result.approved}")
        print(f"     Lookup time:      {elapsed:.3f}s")
    else:
        print(f"\n   ✗ NOT FOUND in CockroachDB")
        print(f"     Lookup time: {elapsed:.3f}s")
except Exception as e:
    print(f"\n   ✗ ERROR during lookup:")
    print(f"     {type(e).__name__}: {e}")
    import traceback
    print("\n   Full traceback:")
    traceback.print_exc()

# Test 2: Runtime lookup (same as order flow)
print("\n2. Runtime saved_manual_review_decision:")
print("-" * 60)
try:
    item = Item(code="73396", name="AVIL 6 AMP", qty=1)
    
    start = time.perf_counter()
    result = saved_manual_review_decision(item)
    elapsed = time.perf_counter() - start
    
    if result:
        print(f"   ✓ SUCCESS: Runtime found correction")
        print(f"     Store Product ID: {result.correct_store_product_id}")
        print(f"     Lookup time:      {elapsed:.3f}s")
    else:
        print(f"   ✗ NOT FOUND via runtime")
        print(f"     Lookup time: {elapsed:.3f}s")
        print(f"     This matches the order run behavior!")
except Exception as e:
    print(f"   ✗ ERROR:")
    print(f"     {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Compare with working item (ACTI-COLLA)
print("\n3. Compare with ACTI-COLLA (known working):")
print("-" * 60)
try:
    item = Item(code="", name="ACTI-COLLA ADVANCE 10 SACHET", qty=1)
    
    start = time.perf_counter()
    result = saved_manual_review_decision(item)
    elapsed = time.perf_counter() - start
    
    if result:
        print(f"   ✓ SUCCESS: Found")
        print(f"     Store Product ID: {result.correct_store_product_id}")
        print(f"     Lookup time:      {elapsed:.3f}s")
    else:
        print(f"   ✗ NOT FOUND")
        print(f"     Lookup time: {elapsed:.3f}s")
except Exception as e:
    print(f"   ✗ ERROR:")
    print(f"     {type(e).__name__}: {e}")

# Test 4: Multiple rapid lookups (simulate race condition)
print("\n4. Rapid sequential lookups (10x):")
print("-" * 60)
success_count = 0
total_time = 0
for i in range(10):
    try:
        start = time.perf_counter()
        result = store.lookup("73396", "AVIL 6 AMP")
        elapsed = time.perf_counter() - start
        total_time += elapsed
        if result:
            success_count += 1
    except Exception:
        pass

print(f"   Success rate: {success_count}/10")
print(f"   Average time: {total_time/10:.3f}s")
if success_count < 10:
    print(f"   ⚠️  Intermittent failures detected!")

print("\n" + "=" * 60)
print("Diagnosis Complete")
print("=" * 60)

print("\nNext steps:")
print("1. If Test 1 succeeds but Test 2 fails:")
print("   → Exception is being silently caught in saved_manual_review_decision")
print("   → Apply error logging fix")
print("\n2. If Test 1 fails:")
print("   → CockroachDB connection or data issue")
print("   → Check DB_PASSWORD in .env")
print("\n3. If rapid lookups fail intermittently:")
print("   → Connection pool exhaustion")
print("   → Increase pool size or add retry logic")
