"""Resolve remove-cart input sources for CLI runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.core.manual_review.manual_review_removal import (
    cart_items_from_manual_review_csv,
    cart_items_from_saved_not_matching,
)
from src.core.errors import ValidationError
from src.core.identity.item_text import normalized_key
from .cli_order_items import load_regular_order_items


def cart_removal_items(
    args: argparse.Namespace,
    excel_loader,
    app_config=None,
) -> list:
    """Return cart-removal items from Excel or manual-review decisions."""
    if getattr(args, "manual_review_scope", "") == "saved-decisions":
        return _limit_items(cart_items_from_saved_not_matching(), args)
    manual_review = getattr(args, "from_manual_review", None)
    if manual_review:
        return _limit_items(cart_items_from_manual_review_csv(Path(manual_review)), args)
    excel = getattr(args, "excel", None)
    if not excel:
        raise ValidationError(
            "Provide --excel or --from-manual-review.",
            hint="Re-run the command with one of these flags.",
        )
    if app_config is not None:
        order_items = _try_load_order_items(app_config, args)
        if order_items is not None:
            return _limit_items(_cart_items_from_order_items(order_items), args)
    return _limit_items(excel_loader(Path(excel)), args)


def _try_load_order_items(app_config, args: argparse.Namespace) -> list | None:
    """Load an order-sheet source with the exact filters used by ``order``.

    A legacy remove sheet may contain only code/name columns. In that case the
    order loader cannot parse the missing quantity column, so ``None`` signals
    the caller to use the legacy cart-removal parser instead.
    """
    try:
        return list(load_regular_order_items(app_config, args))
    except ValueError as error:
        if _is_missing_quantity_column(error, app_config):
            return None
        raise


def _is_missing_quantity_column(error: ValueError, app_config) -> bool:
    """Return whether an order-sheet parse failed only because qty is absent."""
    message = str(error)
    if "Missing required Excel columns" not in message:
        return False
    excel_config = getattr(app_config, "excel", None)
    quantity_column = str(getattr(excel_config, "qty_col", "") or "").strip()
    return bool(quantity_column and quantity_column in message)


def _cart_items_from_order_items(items) -> list:
    """Convert order items to removal items without changing their order."""
    from src.core.cart.cart_removal_items import CartRemovalItem

    result = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        code = str(getattr(item, "code", "") or "").strip()
        name = str(getattr(item, "name", "") or "").strip()
        if not name:
            continue
        key = normalized_key(code, name)
        if key in seen:
            continue
        seen.add(key)
        result.append(CartRemovalItem(code=code, name=name))
    return result


def _limit_items(items, args: argparse.Namespace) -> list:
    """Return at most the first configured number of removal items."""
    limit = int(getattr(args, "limit", 0) or 0)
    if limit < 0:
        raise ValidationError(
            "--limit must be zero or a positive integer.",
            hint="Use --limit 0 to process every item.",
        )
    materialized = list(items)
    return materialized[:limit] if limit else materialized
