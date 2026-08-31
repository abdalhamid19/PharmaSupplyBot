"""API match-only store metadata helpers."""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)



def record_api_match_only_store_metadata(bot, api, match) -> None:
    """Record the API store that match-only would choose without adding to cart."""
    from ..store.tawreed_store_summary import record_single_store
    from ..store.tawreed_store_match_only import (
        record_match_only_choice,
        record_single_store_match_only_choice,
    )

    data = getattr(match, "data", {})
    record_single_store(bot, data)
    if int(data.get("productsCount") or 0) <= 0:
        record_single_store_match_only_choice(bot, data)
        return
    _record_api_multi_store_metadata(bot, api, data)


def _record_api_multi_store_metadata(bot, api, data) -> None:
    """Record the API strategy choice for a multi-store product."""
    from ..store.tawreed_store_summary import record_single_store
    from ..store.tawreed_store_match_only import record_match_only_choice

    try:
        choice = api_match_only_store_choice(bot, api, data)
    except Exception:
        logger.debug("api.match_only_metadata: write failed (non-fatal)")
        return
    if choice:
        record_single_store(bot, choice.store)
    record_match_only_choice(bot, choice)


def api_match_only_store_choice(bot, api, data):
    """Return the API store choice for match-only metadata."""
    from ..products.tawreed_products_flow import _min_disc, _preferred_warehouses, _wh_mode
    from ..store.tawreed_store_selection import choose_next_store_for_remaining_quantity
    from ..store.tawreed_store_snapshot import SOURCE_STORE_DETAILS, record_store_rows

    stores = api.get_store_details(data.get("productId") or data.get("id"))
    record_store_rows(bot, stores, SOURCE_STORE_DETAILS)
    return choose_next_store_for_remaining_quantity(
        stores,
        None,
        _wh_mode(bot),
        bot.skip_item_exception,
        _min_disc(bot),
        _preferred_warehouses(bot),
    )


__all__ = [
    "api_match_only_store_choice",
    "record_api_match_only_store_metadata",
]
