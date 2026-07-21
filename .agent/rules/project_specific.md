---
description: Project-specific rules for Tawreed pharmacy scraping bot configuration and execution
---

# Project-Specific Rules

## Clean Code Policies

### Zero Abbreviations Policy
All identifiers (variables, functions, classes, modules, directories) must be fully descriptive.
- **Forbidden**: `cfg`, `sel`, `pg`, `btn`
- **Required**: `config`, `selector`, `page`, `button`

### 100/20/100 Rule
- **Files**: Must not exceed 100 lines of code.
- **Functions**: Must not exceed 20 lines of code.
- **Line Length**: Must not exceed 100 characters.

## Profile Configuration

### Profile Structure
Each profile in `config.yaml` contains:
- `email`, `password`: Login credentials (from environment variables)
- `pharmacy_switch`: Pharmacy selection settings
- `selectors`: CSS/XPath selectors for UI elements

### Environment Variables
- `TAWREED_EMAIL`: Login email
- `TAWREED_PASSWORD`: Login password

## Selector Management

### Selector Dataclass
Use frozen dataclass for selectors:
```python
@dataclass(frozen=True)
class _Sel:
    login_email: str
    login_password: str
    login_submit: str
    logged_in_marker: str
    # ... more selectors
```

### Selector Fallbacks
Always provide default selectors:
```python
login_email=_get(sel, "login", "email_input", default="input[type='email']")
```

## Order Flow

### Main Methods
1. `auth_interactive()`: Interactive login with session persistence
2. `place_order_from_items()`: Automated order placement from Excel items

### Item Processing
- Read items from Excel using `src/excel.py`
- Each item has: `code`, `name`, `qty`
- Search products by name
- Match products using fuzzy scoring algorithm

## Product Matching

### Matching Algorithm
1. Generate multiple search queries from item name
2. Score each result using:
   - Sequence matching (English/Arabic names)
   - Token overlap score
   - Numeric match score
   - Availability bonus
3. Select best match based on score thresholds

### Score Thresholds
- Exact name match: Always acceptable
- Overlap >= 0.85: Acceptable
- Score >= 12.0 and overlap >= 0.6: Acceptable
- Score >= 16.0 with numeric match: Acceptable

## Warehouse Strategy

### Modes
- `first_available`: Select first warehouse with stock
- `max_available`: Select warehouse with maximum quantity

### Store Selection
When product has multiple stores:
1. Open stores dialog
2. Apply warehouse strategy mode
3. Select appropriate store

## Error Handling

### Artifact Dumping
On failure, save:
- Screenshot: `artifacts/{profile}/{label}.png`
- HTML: `artifacts/{profile}/{label}.html`
- URL: `artifacts/{profile}/{label}.txt`

### Skip vs Fail
- `_SkipItem`: Product not available (skip silently)
- Exception: Technical failure (dump artifacts, fail)

## Session Management

### State File
- Location: `state/{profile_key}.json`
- Persists cookies and localStorage
- Load on startup to avoid re-login
- Save after successful login
