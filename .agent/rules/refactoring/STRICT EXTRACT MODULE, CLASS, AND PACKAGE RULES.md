# Extract Module, Class, and Package Rules for Scraping

This document defines rules for code organization in a Playwright scraping project.

---

## Extract Class Rules

A class **MUST be extracted** only if:

- It groups related functions and properties
- It can be isolated with a single responsibility
- Extracting improves readability

Class extraction **MUST NOT**:

- Change visibility of functions or attributes
- Split behavior into unrelated modules

---

## Extract Package Rules

A package **MUST be extracted** only if:

- Multiple modules share a cohesive responsibility
- It helps enforce clear folder-level separation

---

## Move Function Rules

- Move functions only to modules where they belong logically
- Keep public functions public and private functions private
- Never change the function logic

---

## Dependency Direction

- Dependencies must point inward: config → bot → helpers
- Scraping logic should not depend on presentation
- Keep Playwright-specific code isolated

---

## Configuration Extraction

- Move all selectors to YAML configuration
- Centralize: timeouts, URLs, selectors, credentials
- Keep logic separate from configuration

---

## Line Length Rule

- Every line should be ≤ 100 characters

---

## Forbidden Actions

- Merge unrelated logic into a single module
- Extract trivial modules without responsibility
- Rename entities without instruction
- Change function behavior
- Duplicate code (DRY principle)