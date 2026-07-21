# Function Ordering Rules for Scraping

This document defines how functions should be organized in a Python file.

---

## File Structure (Order)

The file **MUST** be ordered exactly as follows:

1. **Module docstring**
2. **Imports** (standard library, third-party, local)
3. **Constants** (selectors, thresholds)
4. **Dataclasses** (data structures)
5. **Exception classes** (custom exceptions)
6. **Public functions** (main API)
7. **Private functions** (prefixed with `_`)

---

## Module Docstring

- MUST exist
- MUST be first element
- MUST describe module responsibility

---

## Imports Order

```python
# Standard library
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Third-party
from playwright.sync_api import Page, sync_playwright

# Local
from .config import AppConfig, ProfileConfig
from .excel import Item
```

---

## Public Function Rules

- MUST appear before any private function
- MUST have a docstring
- MUST represent main file behavior

---

## Private Function Rules

- MUST be prefixed with `_`
- MUST appear after all public functions
- Helper functions for internal logic

---

## Line Length

- Every line should be ≤ 100 characters

---

## Forbidden Actions

- Change function behavior
- Merge or split logic
- Reorder logic inside a function