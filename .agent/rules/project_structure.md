---
description: Project directory organization for Playwright-based web scraping bot
---

# Project Structure Rules

## Directory Organization

This project is a Playwright-based web scraping bot for pharmacy automation:

```
project_root/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── config.py                # Configuration loading (YAML)
│   ├── excel.py                 # Excel file reading (openpyxl)
│   └── tawreed.py               # Main bot implementation (Playwright)
├── input/                       # Input Excel files
├── artifacts/                   # Debug artifacts (screenshots, HTML)
│   └── {profile_name}/
│       ├── item_error_{code}.png
│       ├── item_error_{code}.html
│       └── order_flow_error.png
├── state/                       # Browser session state (JSON)
│   └── {profile_name}.json
├── config.yaml                  # Profile configurations
├── config.example.yaml          # Configuration template
├── run.py                       # CLI entry point
└── requirements.txt             # Python dependencies
```

## Module Organization Principles

1. **Single Responsibility**: Each module has one clear purpose
   - `config.py`: Configuration management
   - `excel.py`: Excel file parsing
   - `tawreed.py`: Browser automation and scraping

2. **Separation of Concerns**: 
   - Configuration is separate from execution
   - Data parsing is separate from browser logic

3. **State Management**:
   - Session state stored in `state/` directory
   - Each profile has its own state file

## Naming Conventions

- **Modules**: `snake_case` (e.g., `tawreed.py`, `excel.py`)
- **Classes**: `PascalCase` (e.g., `TawreedBot`, `Item`)
- **Private classes**: `_LeadingUnderscore` (e.g., `_Sel`, `_SearchMatch`)
- **Constants**: `UPPER_SNAKE_CASE`

## Import Organization

Use relative imports within the package:
```python
from .config import AppConfig, ProfileConfig
from .excel import Item
```

## File Purposes

### run.py
- CLI entry point
- Parses command-line arguments
- Loads configuration
- Instantiates and runs bot

### src/config.py
- Loads YAML configuration
- Defines `AppConfig` and `ProfileConfig` dataclasses
- Provides selector defaults

### src/excel.py
- Reads Excel files using openpyxl
- Defines `Item` dataclass
- Handles missing/invalid data gracefully

### src/tawreed.py
- Main bot implementation
- Playwright browser automation
- Product search and matching
- Order placement flow
