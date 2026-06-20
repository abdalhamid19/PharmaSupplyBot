#!/usr/bin/env python3
"""Test auto-refresh authentication flow."""

import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from src.tawreed.tawreed_auto_auth import is_token_expired

def test_token_check():
    """Test token expiry detection."""
    state_path = Path("state/wardany.json")
    
    if not state_path.exists():
        print(f"[SKIP] State file not found: {state_path}")
        return True
    
    print(f"[OK] Checking token in: {state_path}")
    
    is_expired = is_token_expired(state_path)
    
    if is_expired:
        print("[EXPIRED] Token is expired or invalid")
    else:
        print("[VALID] Token is still valid")
    
    print(f"\n[INFO] Auto-refresh will trigger: {is_expired}")
    return True

if __name__ == "__main__":
    success = test_token_check()
    exit(0 if success else 1)
