---
description: Best practices for web scraping with Playwright, browser automation, and session management
---

# Best Practices for Web Scraping

## Browser Automation

### Playwright Usage
- Always use `sync_playwright()` context manager for proper cleanup
- Launch browser with appropriate flags (`headless`, `slow_mo` for debugging)
- Use `storage_state` to persist login sessions between runs
- Set appropriate timeouts via `page.set_default_timeout()`

### Session Management
- Save browser state after successful login: `context.storage_state(path=...)`
- Load existing state to avoid re-login: `browser.new_context(storage_state=...)`
- Handle login detection with markers (e.g., specific elements that appear when logged in)

### Error Recovery
- Dump page artifacts (screenshot, HTML) on failure for debugging
- Use try-finally blocks to ensure browser/context closure
- Implement retry logic for transient network errors

## Web Scraping

### Request Handling
- Respect website terms of service
- Use appropriate wait strategies (`wait_until`, `wait_for_load_state`)
- Avoid aggressive scraping that may trigger rate limits
- Implement delays between actions to mimic human behavior

### Element Selection
- Use Playwright's built-in locators (`locator()`, `get_by_text()`, `get_by_role()`)
- Prefer stable selectors over fragile XPath expressions
- Use `first` modifier for ambiguous matches
- Implement fallback selectors for sites that change UI

### Data Extraction
- Wait for elements to be visible/attached before extracting
- Use `inner_text()`, `get_attribute()`, `input_value()` appropriately
- Handle dynamic content with proper waiting strategies

## Data Processing

### Excel/File Operations
- Use `openpyxl` for reading Excel files
- Handle missing values gracefully
- Use proper encoding (`utf-8`) for text files

### Error Handling
```python
try:
    page.goto(url, wait_until="domcontentloaded")
except TimeoutError:
    print(f"Page load timeout: {url}")
    # Dump artifacts for debugging
except Exception as e:
    print(f"Unexpected error: {e}")
    # Cleanup and retry
```

## Configuration

### Environment Variables
- Store credentials in environment variables, not in code
- Use `.env` files with proper `.gitignore` entries
- Provide `.env.example` as a template

### YAML Configuration
- Separate profile configurations (credentials, selectors)
- Use selectors that can adapt to UI changes
- Implement fallback selectors in code

## Security

### Credential Handling
- Never commit credentials to version control
- Use environment variables for sensitive data
- Rotate passwords periodically

### Browser Security
- Run in headless mode for production
- Disable sandbox mode only when necessary (CI environments)
- Clear cookies/storage between runs if needed

## Performance

### Optimization
- Use non-headless mode sparingly (debugging only)
- Minimize page.wait_for_timeout() durations
- Reuse browser contexts when possible
- Disable unnecessary browser features (images, CSS if not needed)

### Resource Management
- Always close browser/context in finally blocks
- Limit concurrent browser instances
- Monitor memory usage in long-running scrapers
