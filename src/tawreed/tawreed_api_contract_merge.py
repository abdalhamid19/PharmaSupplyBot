"""Merge browser-captured Tawreed API requests into the local contract (deprecated)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .tawreed_api_contract import DEFAULT_CONTRACT_PATH, TawreedApiContract, load_api_contract, contract_type, save_contract_requests

# This file is now deprecated - functionality moved to tawreed_api_contract.py
# Keeping for backward compatibility

def save_contract_requests(
    requests: list[dict[str, Any]], path: Path = DEFAULT_CONTRACT_PATH
) -> TawreedApiContract:
    """Persist captured endpoint requests merged with the existing contract (deprecated)."""
    # Delegate to the implementation in tawreed_api_contract.py
    from .tawreed_api_contract import save_contract_requests as _save_contract_requests
    return _save_contract_requests(requests, path)


__all__ = ["save_contract_requests", "contract_type"]
