---
description: Systems engineering approach for Playwright web scraping bot development
---

# Scraping Bot Development Protocol

## Overview

This protocol defines the development approach for the Tawreed pharmacy scraping bot. It transforms the AI from a general assistant into a focused automation engineer.

## Core Principles

### 1. Understand Before Acting
- Always explore the project structure first
- Read existing code to understand patterns
- Check configuration files for context

### 2. Safe Modification Protocol
- **Read first**: Always read the file before editing
- **Backup state**: Don't modify state files in unexpected ways
- **Test incrementally**: Run the bot after each change

### 3. Browser Automation Best Practices
- Use headless mode for production runs
- Debug with non-headless mode and `slow_mo`
- Always save session state after login

### 4. Error Recovery
- Dump artifacts on failure (screenshot, HTML)
- Use specific exceptions (`_SkipItem` for skipped items)
- Log meaningful error messages

## Development Workflow

### Phase 1: Investigation
1. Explore project structure
2. Read relevant source files
3. Understand configuration

### Phase 2: Implementation
1. Make targeted changes
2. Test with small dataset (--limit flag)
3. Verify with artifacts

### Phase 3: Verification
1. Check for syntax errors
2. Run with --limit 1 first
3. Review generated artifacts

## Preferred Libraries

- **Playwright**: Browser automation
- **openpyxl**: Excel file reading
- **PyYAML**: Configuration management
- **pathlib**: File path handling

## Constraints

- Never commit credentials to version control
- Use environment variables for sensitive data
- Keep selectors configurable via YAML
- Handle all exceptions gracefully