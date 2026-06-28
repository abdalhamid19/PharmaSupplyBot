"""API-related methods for TawreedBot."""

from __future__ import annotations

from typing import Iterable

from ..core.cart_removal_items import CartRemovalItem
from ..core.utils.excel import Item
from .tawreed_api import TawreedApiUnavailable


class TawreedBotApi:
    """API-related methods for TawreedBot."""

    def _try_api_order(self, items: Iterable[Item]) -> bool:
        """Run API order flow or return False when browser fallback should handle it."""
        if not self._api_enabled():
            return False
        from .tawreed_api_flow import place_order_with_api

        return self._run_api_or_fallback("order", lambda: place_order_with_api(self, items))

    def _try_api_match_only(self, items: Iterable[Item]) -> bool:
        """Run API match-only flow or return False when browser fallback should handle it."""
        if not self._api_enabled():
            return False
        from .tawreed_api_flow import match_items_only_with_api

        return self._run_api_or_fallback(
            "match-only", lambda: match_items_only_with_api(self, items)
        )

    def _try_api_cart_removal(self, items: Iterable[CartRemovalItem]) -> bool:
        """Run API cart removal or return False when browser fallback should handle it."""
        if not self._api_enabled():
            return False
        from .tawreed_api_flow import remove_cart_items_with_api

        return self._run_api_or_fallback(
            "cart-removal", lambda: remove_cart_items_with_api(self, items)
        )

    def _api_enabled(self) -> bool:
        """Return whether this bot should try the API backend before the browser."""
        return self.execution_mode in {"api", "auto"}

    def _run_api_or_fallback(self, label: str, operation) -> bool:
        """Run one API operation and decide whether browser fallback may continue."""
        try:
            operation()
            self.log(f"{label} completed with Tawreed API backend.")
            return True
        except TawreedApiUnavailable as error:
            if self.execution_mode == "api":
                raise
            self.log(f"{label} API unavailable; falling back to browser: {error}")
            return False
