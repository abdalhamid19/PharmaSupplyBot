"""Helper functions for Tawreed API client (deprecated - functionality moved to tawreed_api_http.py)."""

from pathlib import Path
from typing import Any

from .tawreed_auth_tokens import access_token_from_state
from .tawreed_api_http import _api_origin, _is_trusted_add_to_cart_url, _ensure_cart_item_added


# This file is now deprecated - functionality moved to tawreed_api_http.py
# Keeping for backward compatibility

def _api_origin(base_url: str) -> str:
    """Extract API origin from base URL (deprecated)."""
    from .tawreed_api_http import _api_origin as _api_origin_impl
    return _api_origin_impl(base_url)


def _is_trusted_add_to_cart_url(url: str) -> bool:
    """Return whether a URL is a real add endpoint (deprecated)."""
    from .tawreed_api_http import _is_trusted_add_to_cart_url as _is_trusted_add_to_cart_url_impl
    return _is_trusted_add_to_cart_url_impl(url)


def _ensure_cart_item_added(response: dict[str, Any]) -> None:
    """Raise when an add-to-cart response did not actually add an item (deprecated)."""
    from .tawreed_api_http import _ensure_cart_item_added as _ensure_cart_item_added_impl
    _ensure_cart_item_added_impl(response)


def _auth_headers_from_state(state_path: Path) -> dict[str, str]:
    """Return Tawreed API auth headers extracted from Playwright storage state (deprecated)."""
    from .tawreed_api_http import _auth_headers_from_state as _auth_headers_from_state_impl
    return _auth_headers_from_state_impl(state_path)


__all__ = [
    "_api_origin",
    "_is_trusted_add_to_cart_url",
    "_ensure_cart_item_added",
    "_auth_headers_from_state",
]
