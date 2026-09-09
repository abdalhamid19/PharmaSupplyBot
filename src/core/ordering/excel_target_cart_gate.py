"""Price gate shared by real Tawreed cart flows.

Excel Target matches are persisted before the Tawreed ordering flows start.
This module keeps the resulting comparison at one seam so API and browser
callers cannot drift on item identity, price resolution, or tie handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..database.order_runs_keys import order_run_item_key
from ..database.order_runs_paths import default_order_runs_db
from ..database.order_runs_store import OrderRunsStore
from ..pricing import resolve_store_prices
from ..utils.excel import Item


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
    ) -> CartGateDecision:
        """Return whether the Tawreed candidate is blocked by Excel Target.

        The comparison is intentionally inclusive: an Excel purchase price
        lower than or equal to the resolved Tawreed purchase price wins. A
        missing price on either side is not comparable and therefore never
        blocks ordering.
        """
        excel_price = self._lowest_excel_purchase_price(run_key, item)
        tawreed_price = resolve_store_prices(tawreed_store).purchase_price
        blocked = (
            excel_price is not None
            and tawreed_price is not None
            and excel_price <= tawreed_price
        )
        reason = _blocked_reason(excel_price, tawreed_price) if blocked else ""
        return CartGateDecision(blocked, excel_price, reason)

    def _lowest_excel_purchase_price(
        self,
        run_key: str,
        item: Item,
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
               and purchase_price is not null
            """,
            (run_key, item_key),
        )
        value = rows[0][0] if rows else None
        return float(value) if value is not None else None


def _blocked_reason(
    excel_purchase_price: float,
    tawreed_purchase_price: float,
) -> str:
    """Return a concise operator-facing reason for a blocked cart add."""
    return (
        "Excel Target purchase price "
        f"{excel_purchase_price:.2f} <= Tawreed purchase price "
        f"{tawreed_purchase_price:.2f}"
    )


__all__ = ["CartGateDecision", "ExcelTargetCartGate"]
