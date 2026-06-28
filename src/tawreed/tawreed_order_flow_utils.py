"""Utility functions for Tawreed order flow."""


def _artifact_details(label: str, error: Exception, **extra: object) -> str:
    """Build plain-text diagnostic details for saved failure artifacts."""
    lines = [f"label={label}", f"error_type={type(error).__name__}", f"error={error}"]
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _save_api_contract_capture(captured: list[dict]) -> None:
    """Save API contract capture data."""
    try:
        from .tawreed_api_contract import save_api_contract_capture
        save_api_contract_capture(captured)
    except Exception:
        pass
