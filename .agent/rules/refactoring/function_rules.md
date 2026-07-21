# Clean Code Function Rules for Web Scraping

## Function Length Rules

1. **Keep functions short**
   - Ideal: 10-15 lines
   - Acceptable: 20-30 lines (for complex Playwright operations)

2. **Line width limit**
   - Each line should not exceed 100 characters

## Code Block Rules

3. **Single action per block**
   - Each block should contain one primary action
   - Reduces indentation depth

## Levels of Abstraction

4. **What vs How**
   - High-level functions describe what they do
   - Lower-level functions handle how
   - Example: `place_order_from_items()` calls `_add_item()`, `_search_products()`

## Refactoring Practices

5. **Extract complex conditions**
   - Move complex conditions to separate functions: `is_match_acceptable()`

6. **Separate responsibilities**
   - Keep Playwright operations separate from business logic

7. **Abstract selector logic**
   - Encapsulate selectors in dedicated dataclasses: `_Sel`

8. **Early return**
   - Use early exits to reduce nesting

9. **Reduce nested logic**
   - Maximum nesting depth: 3 levels
   - Extract nested blocks into separate functions

10. **Command-Query Separation**
    - Commands: Change state, return None
    - Queries: Return data, don't change state

## Golden Rules

11. **Step-down reading**
    - Code reads top-to-bottom like a story

12. **Explicit is better than implicit**
    - Clear variable names, no magic

13. **Readable for others**
    - Anyone should understand the flow

## Function Arguments

14. **Number of Parameters**
    | Count | Type | Rating |
    |---|---|---|
    | **0-1** | Ideal | ✅ |
    | **2** | Acceptable | ⚠️ |
    | **3+** | Refactor | ❌ |

15. **Reduce Parameters via**
    - Group related data into dataclasses
    - Pass only what's needed

16. **Avoid**
    - Boolean parameters (split into functions)
    - Passing entire objects when only fields needed
