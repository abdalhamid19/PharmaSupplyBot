"""Shared item text normalization helpers."""

from __future__ import annotations


def normalized_key(code: object, name: object) -> tuple[str, str]:
    """Return a normalized comparable product key."""
    return normalize_code(code), normalize_name(name)


def normalize_code(value: object) -> str:
    """Return a stable code string for comparisons."""
    text = normalized_cell_text(value).lower()
    if text in {"nan", "none"}:
        return ""
    if text.endswith(".0"):
        return text[:-2]
    return text


def normalize_name(value: object) -> str:
    """Return a stable item-name string for comparisons."""
    return " ".join(normalized_cell_text(value).lower().split())


def normalized_cell_text(value: object) -> str:
    """Return spreadsheet cell text safely without pandas artifacts."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value).strip()


def display_code_text(value: object) -> str:
    """Return code text suitable for saving and display."""
    text = normalized_cell_text(value)
    if text.endswith(".0"):
        return text[:-2]
    return text


def normalize_prevented_compare_name(value: object) -> str:
    """Return a stable name string for prevented comparison.
    
    Normalize name by:
    - Converting to lowercase
    - Normalizing spaces
    - Removing trailing punctuation from the name
    - Removing punctuation from ends of each token after split
    - Preserving dots inside numbers (e.g., 10.000, 0.3%)
    
    إرجاع نص اسم مستقر للمقارنة الممنوعة.
    """
    text = normalized_cell_text(value).lower()
    punctuation = ".,;:!?،؛"

    def _is_number_with_decimal(token: str) -> bool:
        """Check if token looks like a number with decimal point."""
        if token[-1] != "." or len(token) <= 1:
            return False
        return token[:-1].replace(".", "").replace("%", "").isdigit()

    def _clean_token(token: str) -> str:
        """Remove edge punctuation, preserving decimal dots in numbers."""
        while token and token[0] in punctuation:
            token = token[1:]
        while token and token[-1] in punctuation:
            if _is_number_with_decimal(token):
                break
            token = token[:-1]
        return token

    tokens = [_clean_token(t) for t in text.split() if _clean_token(t)]
    return " ".join(tokens)
