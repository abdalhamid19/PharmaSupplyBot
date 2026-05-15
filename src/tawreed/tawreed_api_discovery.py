"""Capture Tawreed API requests from browser fallback runs."""

from __future__ import annotations

from typing import Any

from .tawreed_api_contract import DEFAULT_CONTRACT_PATH, TawreedApiContract
from .tawreed_api_contract_merge import contract_type, save_contract_requests


def begin_api_contract_capture(page) -> list[dict[str, Any]]:
    """Attach a lightweight request listener and return its capture buffer."""
    captured: list[dict[str, Any]] = []
    if on_event := getattr(page, "on", None):
        on_event("request", lambda request: _capture_request(request, captured))
    return captured


def save_api_contract_capture(
    captured: list[dict[str, Any]], path=DEFAULT_CONTRACT_PATH
) -> TawreedApiContract:
    """Persist captured endpoints merged with any existing local contract."""
    return save_contract_requests(captured, path)


def _capture_request(request, captured: list[dict[str, Any]]) -> None:
    if str(request.method).upper() != "POST":
        return
    url = str(request.url)
    if not contract_type(url):
        return
    captured.append({"url": url, "body": _request_body(request)})


def _request_body(request) -> dict[str, Any]:
    try:
        body = request.post_data_json
        return body() if callable(body) else body
    except Exception:
        return {}
