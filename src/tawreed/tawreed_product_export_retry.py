"""Retry helpers for Tawreed product export API calls."""

from __future__ import annotations

import time
from typing import Any

EXPORT_API_RETRY_ATTEMPTS = 3
EXPORT_API_TIMEOUT_MS = 60_000
_RETRY_DELAYS_SECONDS = (1.0, 2.0)


def post_product_export_json(
    request_context: Any,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    """POST one product export API request with bounded retries."""
    last_error: Exception | None = None
    for attempt in range(EXPORT_API_RETRY_ATTEMPTS):
        try:
            return _post_once(request_context, url, body, headers)
        except Exception as error:
            last_error = error
            if attempt == EXPORT_API_RETRY_ATTEMPTS - 1:
                break
            time.sleep(_RETRY_DELAYS_SECONDS[attempt])
    raise RuntimeError(f"Tawreed products export API request failed: {last_error}")


def _post_once(
    request_context: Any,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    response = request_context.post(
        url,
        data=body,
        headers=headers,
        timeout=EXPORT_API_TIMEOUT_MS,
    )
    if not response.ok:
        raise RuntimeError(
            f"Tawreed products export API returned HTTP {response.status}"
        )
    return response.json()
