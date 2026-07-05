# Auto-Save Safety Validation Implementation Summary

## Overview
This document summarizes the safety validation functions implemented to prevent auto-saving matches with conflicts and to validate manual review matches before accepting them with score 999.

## Changes Made

### 1. Safety Validation for Manual Review Matches (Score 999)

**File: `src/core/manual_review/manual_review_helpers.py`**

Added validation before accepting manual review matches with score 999:

- `_validate_manual_review_match`: Main validation function (35 lines)
  - Checks product ID match (saved vs current)
  - Checks manufacturer/brand conflict
  - Checks name consistency (saved vs current)

- `_validate_product_id_match`: Checks if saved product ID still matches (19 lines)
- `_validate_manufacturer_match`: Checks for manufacturer/brand conflict (20 lines)
- `_validate_name_consistency`: Checks if saved name changed significantly (24 lines)
- `_extract_item_manufacturer`: Extracts manufacturer from item name (9 lines)
- `_extract_candidate_manufacturer`: Extracts manufacturer from candidate data (15 lines)
- `_is_major_name_change`: Heuristic to detect major name changes (22 lines)

**Behavior:**
- If validation fails, the match is NOT added to the cart
- Instead, it returns None, causing the item to go to manual review
- A warning is logged with the rejection reason

### 2. Auto-Save Conflict Prevention

**File: `src/core/manual_review/manual_review_helpers.py`**

Added `should_skip_auto_save` function (37 lines):
- Checks for conflict-related rejection reasons (conflict, manufacturer, brand, semantic)
- Checks for manufacturer conflict between item and candidate
- Returns `(should_skip, reason)` tuple

**File: `src/core/manual_review/manual_review_runtime.py`**

Added public wrapper `should_skip_auto_save_verified_match` (19 lines):
- Can be imported and used in `src/tawreed/order/tawreed_order_summary_build.py`
- Prevents saving matches that have conflicts or were rejected due to conflicts

### 3. Updated Function Signatures

Updated the following functions to pass item and decision for validation:
- `_find_manual_review_match`: Added `item` and `decision` parameters
- `_manual_review_id_match`: Added `item` and `decision` parameters
- `_manual_review_name_match`: Added `item` and `decision` parameters
- `_find_name_match_in_candidates`: Added `item` and `decision` parameters

## How to Use in `_auto_save_verified_match`

**File: `src/tawreed/order/tawreed_order_summary_build.py`** (not modified, instructions provided)

To complete the implementation, update `_auto_save_verified_match`:

```python
def _auto_save_verified_match(item: Item, decision) -> None:
    """Auto-save verified matches to manual review store."""
    if not decision or not decision.best_match:
        return

    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (decision.final_reason or ""):
        return

    # NEW: Check for conflicts before auto-saving
    # التحقق من التضاربات قبل الحفظ التلقائي
    from src.core.manual_review.manual_review_runtime import should_skip_auto_save_verified_match
    
    should_skip, skip_reason = should_skip_auto_save_verified_match(
        item, match.data, decision.final_reason
    )
    if should_skip:
        logger.warning(f"Auto-save skipped for {item.code}/{item.name}: {skip_reason}")
        return

    store = ManualReviewStore(DEFAULT_MANUAL_REVIEW_DB)
    if _preserve_existing_decision(store.lookup(item.code, item.name)):
        return

    _create_and_save_decision(item, match, store)
```

## Safety Checks Performed

### Manual Review Match Validation (Score 999)

1. **Product ID Match**: Verifies the saved product ID still matches the current candidate
2. **Manufacturer Conflict**: Checks if item manufacturer conflicts with candidate manufacturer
3. **Name Consistency**: Checks if saved name changed significantly (different product)

### Auto-Save Conflict Prevention

1. **Conflict-related rejection**: Skips if rejection reason contains conflict keywords
2. **Manufacturer conflict**: Checks if item manufacturer conflicts with candidate manufacturer

## Arabic Comments

All new functions include Arabic comments (#) alongside English documentation:
- `# التحقق من صحة تطابق المراجعة اليدوية قبل قبوله بدرجة 999` - Validate manual review match before accepting with score 999
- `# التحقق من تضارب الشركة المصنعة` - Check manufacturer conflict
- `# التحقق من أن الحفظ التلقائي يجب تخطيه بسبب التضاربات أو المشاكل` - Check if auto-save should be skipped due to conflicts

## Code Quality Compliance

All functions comply with project guidelines:
- Function length <= 50 lines (verified: max 37 lines)
- Separation of concerns (validation logic in helpers, orchestration in runtime)
- Clear docstrings with Arabic translations using # comments
- Type hints on public APIs
- No modification to files outside the allowed scope

## Files Modified

1. `src/core/manual_review/manual_review_helpers.py` - Added validation helpers
2. `src/core/manual_review/manual_review_runtime.py` - Added public API wrapper and updated imports

## Function Lengths Summary

### manual_review_helpers.py
- `_validate_manual_review_match`: 35 lines
- `_validate_product_id_match`: 19 lines
- `_validate_manufacturer_match`: 20 lines
- `_validate_name_consistency`: 24 lines
- `_extract_item_manufacturer`: 9 lines
- `_extract_candidate_manufacturer`: 15 lines
- `_is_major_name_change`: 22 lines
- `should_skip_auto_save`: 37 lines
- `_find_name_match_in_candidates`: 34 lines
- `_manual_review_id_match`: 33 lines
- `_manual_review_name_match`: 23 lines

### manual_review_runtime.py
- `should_skip_auto_save_verified_match`: 19 lines
- `manual_review_match`: 24 lines

All functions are within the 50-line limit.
