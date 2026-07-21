---
description: Python coding standards for Playwright automation and web scraping projects
---

# Coding Standards for Web Scraping

## Python Style Guide

### Code Formatting
- Follow PEP 8 style guide
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters (relaxed for readability)
- Use type hints for function parameters and return values

### Playwright-Specific Patterns
```python
def scrape_products(page: Page, query: str) -> list[dict]:
    """
    Search for products and extract results.
    
    Args:
        page: Playwright page object
        query: Search query string
        
    Returns:
        List of product dictionaries
        
    Raises:
        TimeoutError: When search elements don't load
    """
    search = page.locator("#search-input").first
    search.fill(query)
    search.press("Enter")
    # Wait for results
    page.wait_for_selector(".product-row", timeout=5000)
    # Extract data
    return []
```

### Error Handling
- Always use try-except blocks for browser operations
- Provide meaningful error messages with context
- Dump artifacts (screenshot, HTML) on failure for debugging
- Return None or empty collections on failure (document this behavior)

### Browser Operations
- Always use context managers: `with sync_playwright() as p:`
- Set appropriate timeouts: `page.set_default_timeout()`
- Use proper wait strategies: `wait_until="domcontentloaded"`, `wait_for_load_state("networkidle")`
- Close resources in finally blocks

### File Operations
- Always check if directories exist before writing
- Use `Path.mkdir(parents=True, exist_ok=True)` for directory creation
- Use context managers for file operations
- Use `encoding="utf-8"` for text files

### Naming Conventions
- Variables: `snake_case`
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private functions: `_leading_underscore`
- Dataclasses for selectors: `_Sel`, `_SearchMatch`

### Documentation
- All public functions must have docstrings
- Document Playwright-specific parameters (page, browser, context)
- Include timeout values in docstrings
- Explain when exceptions are raised
