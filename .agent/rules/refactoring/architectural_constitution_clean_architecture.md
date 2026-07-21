# Architectural Constitution for Web Scraping

This document defines architectural rules for the Playwright scraping bot.

---

## Rule 0 — Single Responsibility

**Every module, class, and function must have exactly one reason to change.**

- `config.py`: Configuration loading only
- `excel.py`: Excel parsing only
- `tawreed.py`: Browser automation only

---

## 1. Layer Separation

### Rule

**Separate concerns into distinct modules.**

- **Configuration**: YAML loading, profile management
- **Data**: Excel parsing, item structures
- **Automation**: Playwright operations, scraping logic

---

## 2. No Infrastructure Leakage

### Rule

**Business logic should not depend on Playwright specifics.**

- Keep page operations in `tawreed.py`
- Keep data structures in `excel.py`
- Configuration should be injectable

---

## 3. Code Quality Rules

### Rule

**Code must be concise and readable.**

- **Files**: Max 150 lines (relaxed for scraping)
- **Functions**: Max 30 lines
- **Line Width**: Max 100 characters

---

## 4. Explicit Dependencies

### Rule

**All dependencies must be explicitly declared.**

- No global state
- Clear input/output contracts
- Use dataclasses for structured data

---

## 5. Error Handling

### Rule

**Fail gracefully with meaningful errors.**

- Use custom exceptions (`_SkipItem`)
- Dump artifacts on failure
- Log meaningful messages

---

## 6. Session Management

### Rule

**Persist browser state properly.**

- Save state after login
- Load state on startup
- Handle state file errors gracefully

---

## 7. Selector Management

### Rule

**Keep selectors configurable.**

- Store selectors in YAML
- Provide defaults in code
- Support fallback selectors

---

## Final Directive

> **Keep it simple, maintainable, and testable.**