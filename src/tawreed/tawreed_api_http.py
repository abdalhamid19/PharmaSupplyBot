"""HTTP request methods and helper functions for Tawreed API client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .tawreed_auth_tokens import access_token_from_state


# ============================================================================
# HTTP Request Methods
# ============================================================================

def _post_json(client, url: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST JSON with saved auth state without opening Chromium."""
    from .tawreed_api_contract import TawreedApiUnavailable
    
    response = client._ensure_request_context().post(url, data=body, timeout=60_000)
    if not response.ok:
        raise TawreedApiUnavailable(
            f"Tawreed API returned HTTP {response.status}: {response.status_text}"
        )
    payload = response.json()
    
    # Check if response indicates failure
    if isinstance(payload, dict):
        status = payload.get("status")
        if status and status >= 400:
            raise TawreedApiUnavailable(
                f"Tawreed API error {status}: {payload.get('message', 'Unknown error')}"
            )
    
    return payload if isinstance(payload, dict) else {"data": payload}


# ============================================================================
# Helper Functions
# ============================================================================

def _api_origin(base_url: str) -> str:
    """Extract API origin from base URL."""
    if "seller.tawreed.io" in base_url:
        return "https://api.tawreed.io"
    return base_url.split("#/", 1)[0].rstrip("/")


def _is_trusted_add_to_cart_url(url: str) -> bool:
    """Return whether a URL is a real add endpoint and not the cart-read endpoint.

    The Tawreed cart-read endpoint ``.../shopping/carts/items`` returns HTTP 200
    with the existing cart, so posting to it reports a false ``added-to-cart``
    while nothing is added. A trusted add endpoint must be the dedicated
    ``.../carts/items/add`` route, never the bare cart-read route.
    """
    path = str(url or "").split("?", 1)[0].rstrip("/").lower()
    if not path:
        return False
    return not path.endswith("carts/items")


def _ensure_cart_item_added(response: dict[str, Any]) -> None:
    """Raise when an add-to-cart response did not actually add an item.

    The Tawreed cart-read endpoint returns HTTP 200 with an empty ``data`` list
    when the wrong endpoint or payload is used, which previously made the bot
    report a false ``added-to-cart`` status. Treat an empty response as failure
    so the caller can fall back to the browser flow.
    """
    from .tawreed_api_contract import TawreedApiUnavailable
    
    data = response.get("data") if isinstance(response, dict) else None
    if not data:
        raise TawreedApiUnavailable(
            "Tawreed add-to-cart returned no cart data; the item was not added."
        )


def _auth_headers_from_state(state_path: Path) -> dict[str, str]:
    """Return Tawreed API auth headers extracted from Playwright storage state."""
    token = access_token_from_state(state_path)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


__all__ = [
    "_post_json",
    "_api_origin",
    "_is_trusted_add_to_cart_url",
    "_ensure_cart_item_added",
    "_auth_headers_from_state",
]
