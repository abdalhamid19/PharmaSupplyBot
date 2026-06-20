"""Tests for Tawreed automatic auth refresh helpers."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.tawreed.selectors import _selectors
from src.tawreed.tawreed_auto_auth import auto_refresh_auth_if_needed
from src.tawreed.tawreed_headless_auth_refresh import (
    products_page_url,
    require_env_credentials,
)


class TawreedAutoAuthTests(unittest.TestCase):
    """Validate token-refresh orchestration without opening Playwright."""

    def test_auto_refresh_skips_when_token_is_valid(self) -> None:
        with patch("src.tawreed.tawreed_auto_auth.is_token_expired", return_value=False):
            with patch("src.tawreed.tawreed_auto_auth.run_headless_auth_refresh") as refresh:
                auto_refresh_auth_if_needed(
                    "https://seller.tawreed.io/#/login",
                    Path("state/wardany.json"),
                    runtime_config=object(),
                    selectors=object(),
                    profile_key="wardany",
                )

        refresh.assert_not_called()

    def test_auto_refresh_runs_headless_auth_when_token_is_expired(self) -> None:
        with patch(
            "src.tawreed.tawreed_auto_auth.is_token_expired",
            side_effect=[True, False],
        ):
            with patch("src.tawreed.tawreed_auto_auth.run_headless_auth_refresh") as refresh:
                auto_refresh_auth_if_needed(
                    "https://seller.tawreed.io/#/login",
                    Path("state/wardany.json"),
                    runtime_config=object(),
                    selectors=object(),
                    profile_key="wardany",
                )

        refresh.assert_called_once()

    def test_missing_env_credentials_raise_clear_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                require_env_credentials("wardany")

        self.assertIn("TAWREED_EMAIL", str(context.exception))
        self.assertIn("wardany", str(context.exception))

    def test_products_page_url_uses_tawreed_route(self) -> None:
        self.assertEqual(
            products_page_url("https://seller.tawreed.io/#/login"),
            "https://seller.tawreed.io/#/catalog/store-products/dv/",
        )

    def test_default_login_selector_supports_username_field(self) -> None:
        config = SimpleNamespace(selectors={}, warehouse_strategy={})

        selectors = _selectors(config)

        self.assertIn("#username", selectors.login_email)
        self.assertIn("input[name='username']", selectors.login_email)
        self.assertIn("button:has-text('دخول')", selectors.login_submit)


if __name__ == "__main__":
    unittest.main()
