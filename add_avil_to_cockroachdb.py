"""
إضافة تصحيح AVIL 6 AMP إلى CockroachDB Cloud
استخدام النظام الموجود: ManualReviewStore
"""
from src.core.manual_review_store import ManualReviewStore, ManualReviewDecision

def add_avil_correction():
    """إضافة تصحيح AVIL 6 AMP إلى CockroachDB"""
    
    print("Connecting to CockroachDB...")
    store = ManualReviewStore()
    
    # إنشاء التصحيح
    avil_correction = ManualReviewDecision(
        item_code="73396",
        item_name="AVIL 6 AMP",
        approved=True,
        correct_store_product_id="2640615",
        correct_product_name="AVIL 45.5 MG / 2 ML 6 I.M. AMPS.",
        correct_product_name_ar="افيل 45.5 مجم / 2 مل 6 امبول",
        run_id="20260622_1535",
        manual_decision="approved_match"
    )
    
    print("\nSaving AVIL correction to CockroachDB...")
    try:
        store.upsert(avil_correction)
        print("OK - Correction saved successfully")
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    # التحقق من الحفظ
    print("\nVerifying saved correction...")
    try:
        saved = store.lookup("73396", "AVIL 6 AMP")
        if saved:
            print(f"OK - Found correction:")
            print(f"  Item: {saved.item_code} | {saved.item_name}")
            print(f"  Decision: {saved.manual_decision}")
            print(f"  Store Product ID: {saved.correct_store_product_id}")
            print(f"  Product Name EN: {saved.correct_product_name}")
            print(f"  Product Name AR: {saved.correct_product_name_ar}")
            return True
        else:
            print("WARNING: Correction not found after save")
            return False
    except Exception as e:
        print(f"ERROR during verification: {e}")
        return False

if __name__ == "__main__":
    success = add_avil_correction()
    if success:
        print("\n=== SUCCESS ===")
        print("AVIL 6 AMP correction is now in CockroachDB")
        print("Future runs will use this correction automatically")
    else:
        print("\n=== FAILED ===")
        print("Please check database connection and credentials")
