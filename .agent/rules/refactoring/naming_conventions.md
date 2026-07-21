# Clean Code Naming Conventions for Web Scraping

## Core Philosophy

- **Code as English**: Code must be readable and understandable
- **Explicit over Implicit**: Clarity is paramount
- **Domain Language**: Use terms from the automation domain

## Do's: Meaningful Naming

- **Intention-Revealing Names**: Names must tell what a variable/function does
- **Parts of Speech**:
  - Variables/Classes: Nouns (e.g., `TawreedBot`, `Item`)
  - Functions: Verbs (e.g., `search_products`, `add_item`)
- **Pronounceable & Searchable**: Avoid prefixes like `sel_`, `btn_`
- **Naming by Scope**: Longer names for wider scope

## Naming Patterns for Scraping

| Element | Pattern | Example |
|---------|---------|---------|
| Bot class | `{Site}Bot` | `TawreedBot` |
| Selector class | `_Sel` | `_Sel` |
| Search match | `_SearchMatch` | `_SearchMatch` |
| Item data | `{Entity}Item` | `Item` |
| Private function | `_action_verb` | `_search_products` |
| Public function | `action_verb` | `place_order_from_items` |

## Don'ts

- **Avoid Abbreviations**: Use `password` not `pwd`, `quantity` not `qty`
- **Avoid Noise Words**: Don't use `data`, `info`, `obj` in names
- **Avoid Ambiguous Characters**: Don't use `l`, `O`, `I` that look like `1`, `0`
- **No Hungarian Notation**: Don't prefix with types (`str_name`, `int_count`)
- **No Mental Mapping**: Don't use single letters (`c`, `r`, `p`)

## Standard Patterns

- `getX`: Retrieve data (e.g., `get_product`)
- `isX`: Boolean check (e.g., `is_logged_in`)
- `find_best_X`: Search and select (e.g., `find_best_product_match`)
- `_X_button`: Selector for button elements
- `_X_input`: Selector for input elements