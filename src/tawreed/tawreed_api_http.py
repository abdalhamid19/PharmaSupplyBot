"""HTTP request methods for Tawreed API client."""

from __future__ import annotations

from typing import Any

from .tawreed_api_exceptions import TawreedApiUnavailable


def _post_json(client, url: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST JSON with saved auth state without opening Chromium."""
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


__all__ = ["_post_json"]
