"""Capture Tawreed network requests and save a local API endpoint contract."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from src.core.config.config import load_config
from src.tawreed.tawreed_api_contract import (
    DEFAULT_CONTRACT_PATH,
    save_discovered_api_contract,
)
from src.tawreed.tawreed_session import open_order_page


def main() -> int:
    """Run API discovery for one authenticated Tawreed profile."""
    args = _parser().parse_args()
    config = load_config(Path(args.config))
    state_path = Path("state") / f"{args.profile}.json"
    if not state_path.exists():
        raise SystemExit(f"Missing session state: {state_path}")
    captured = _capture_requests(config, state_path, int(args.seconds))
    contract = save_discovered_api_contract(captured, Path(args.output))
    print(json.dumps({"captured": len(captured), **contract.__dict__}, ensure_ascii=False))
    return 0


def _capture_requests(config: Any, state_path: Path, seconds: int) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser, context, page = open_order_page(
            playwright, config.runtime, state_path, debug_browser=True
        )
        page.on("request", lambda request: _capture_request(captured, request))
        try:
            page.goto(config.base_url, wait_until="domcontentloaded")
            print("Use the browser to search, add/remove cart, then wait.")
            time.sleep(max(5, seconds))
        finally:
            context.close()
            browser.close()
    return captured


def _capture_request(captured: list[dict[str, Any]], request: Any) -> None:
    url = request.url
    if not _is_tawreed_api_url(url):
        return
    captured.append(
        {
            "method": request.method,
            "url": url,
            "body": _json_body(request.post_data or ""),
        }
    )


def _is_tawreed_api_url(url: str) -> bool:
    return "tawreed" in url and "/rest/" in url


def _json_body(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--profile", default="wardany")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--output", default=str(DEFAULT_CONTRACT_PATH))
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
