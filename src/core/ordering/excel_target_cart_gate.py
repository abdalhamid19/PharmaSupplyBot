"""Price gate shared by real Tawreed cart flows.

Excel Target matches are persisted before the Tawreed ordering flows start.
This module keeps the resulting comparison at one seam so API and browser
callers cannot drift on item identity, price resolution, or tie handling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..database.order_runs_keys import order_run_item_key
from ..database.order_runs_paths import default_order_runs_db
from ..database.order_runs_store import OrderRunsStore
from ..pricing import resolve_store_prices
from ..utils.excel import Item
from .warehouse_order_policy import PRICE_TOLERANCE_EGP
from ...tawreed.store.tawreed_pricing import (
    discount_value_as_percent,
    first_discount_value,
)


@dataclass(frozen=True)
class CartGateDecision:
    """The result of comparing one Tawreed candidate with Excel Target offers."""

    blocked: bool
    excel_purchase_price: float | None
    reason: str


class ExcelTargetCartGate:
    """Decide whether an Excel Target offer must block a Tawreed cart add."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Open the order-runs database at the configured path.

        ``None`` follows the same default path resolver as order-run
        persistence. Callers with an application-configured path should pass
        it explicitly so the gate reads the database populated by that run.
        """
        self.db_path = Path(db_path) if db_path is not None else default_order_runs_db()
        self._store = OrderRunsStore(self.db_path)

    def evaluate(
        self,
        run_key: str,
        item: Item,
        tawreed_store: dict[str, Any],
        *,
        min_discount_percent: float | None = None,
    ) -> CartGateDecision:
        """Return whether the Tawreed candidate is blocked by Excel Target.

        An Excel price less than 0.25 EGP above the resolved Tawreed price wins.
        A missing price on either side is not comparable and never blocks.
        """
        minimum = self._effective_min_discount_percent(
            run_key, min_discount_percent
        )
        tawreed_price = (
            resolve_store_prices(tawreed_store).purchase_price
            if _discount_percent(tawreed_store) >= minimum - 0.001
            else None
        )
        return self._decision(
            self._lowest_excel_purchase_price(run_key, item, minimum), tawreed_price
        )

    def evaluate_candidates(
        self,
        run_key: str,
        item: Item,
        tawreed_stores: list[dict[str, Any]],
        *,
        min_discount_percent: float | None = None,
    ) -> CartGateDecision:
        """Evaluate the cheapest valid Tawreed price before cart mutation."""
        minimum = self._effective_min_discount_percent(
            run_key, min_discount_percent
        )
        tawreed_prices = []
        for store in tawreed_stores:
            if (
                _available_quantity(store) <= 0
                or _discount_percent(store) < minimum - 0.001
            ):
                continue
            resolved = resolve_store_prices(store)
            if (
                resolved.purchase_price is not None
                and resolved.purchase_price > 0
            ):
                tawreed_prices.append(resolved.purchase_price)
        valid_prices = [price for price in tawreed_prices if price is not None]
        tawreed_price = min(valid_prices) if valid_prices else None
        return self._decision(
            self._lowest_excel_purchase_price(run_key, item, minimum), tawreed_price
        )

    def lowest_excel_purchase_price(
        self,
        run_key: str,
        item: Item,
        min_discount_percent: float | None = None,
    ) -> float | None:
        """Return the lowest persisted Excel Target purchase price for an item."""
        minimum = self._effective_min_discount_percent(
            run_key, min_discount_percent
        )
        return self._lowest_excel_purchase_price(run_key, item, minimum)

    @staticmethod
    def _decision(
        excel_price: float | None, tawreed_price: float | None
    ) -> CartGateDecision:
        blocked = (
            excel_price is not None
            and tawreed_price is not None
            and excel_price < tawreed_price + PRICE_TOLERANCE_EGP
        )
        reason = _blocked_reason(excel_price, tawreed_price) if blocked else ""
        return CartGateDecision(blocked, excel_price, reason)

    def _lowest_excel_purchase_price(
        self,
        run_key: str,
        item: Item,
        min_discount_percent: float = 0.0,
    ) -> float | None:
        """Read the cheapest resolved Excel purchase price for one run item."""
        if not run_key:
            return None
        item_key = order_run_item_key(item.code, item.name)
        rows = self._store.db.execute_query(
            """
            select min(purchase_price)
              from run_item_stores
             where run_key = ?
               and item_key = ?
               and source in ('excel_target', 'excel-target')
               and purchase_price > 0
               and purchase_price < 1e308
               and available_qty > 0
               and coalesce(discount_percent, 0) >= ? - 0.001
            """,
            (run_key, item_key, float(min_discount_percent)),
        )
        value = rows[0][0] if rows else None
        return float(value) if value is not None else None

    def _effective_min_discount_percent(
        self, run_key: str, override: float | None
    ) -> float:
        """Prefer an explicit live setting, otherwise reuse the saved run rule."""
        if override is not None:
            return _normalized_minimum(override)
        rows = self._store.db.execute_query(
            "select min_discount_pct from runs where run_key = ?", (run_key,)
        )
        value = rows[0][0] if rows else None
        return _normalized_minimum(value)


def _blocked_reason(
    excel_purchase_price: float,
    tawreed_purchase_price: float,
) -> str:
    """Return a concise operator-facing reason for a blocked cart add."""
    return (
        "Excel Target purchase price "
        f"{excel_purchase_price:.2f} is lower than or within "
        f"{PRICE_TOLERANCE_EGP:g} EGP of "
        f"Tawreed purchase price {tawreed_purchase_price:.2f}"
    )


def _available_quantity(store: dict[str, Any]) -> int:
    """Return the positive stock quantity exposed by a Tawreed offer."""
    value = store.get("available_qty", store.get("availableQuantity", 0))
    try:
        return max(0, int(float(str(value).replace(",", ""))))
    except (TypeError, ValueError):
        return 0


def _discount_percent(store: dict[str, Any]) -> float:
    """Return the Tawreed discount as a percentage for floor comparisons."""
    return max(0.0, discount_value_as_percent(first_discount_value(store)))


def _normalized_minimum(value: Any) -> float:
    try:
        minimum = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, minimum) if math.isfinite(minimum) else 0.0


__all__ = ["CartGateDecision", "ExcelTargetCartGate"]
