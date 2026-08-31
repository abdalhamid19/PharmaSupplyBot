"""Search rows without productId must record their own store as the winner."""

from __future__ import annotations

from types import SimpleNamespace

from src.tawreed.api.tawreed_api_match_only_metadata import (
    record_api_match_only_store_metadata,
)
from src.tawreed.store.tawreed_store_snapshot import (
    captured_store_rows,
    captured_store_selections,
)


class _Match:
    def __init__(self, data: dict) -> None:
        self.data = data


class _Api:
    def __init__(self) -> None:
        self.store_details_calls: list = []

    def get_store_details(self, product_id) -> list:
        self.store_details_calls.append(product_id)
        return [{"storeProductId": 1, "storeName": "خ"}]


def _bot() -> SimpleNamespace:
    return SimpleNamespace()


def _row() -> dict:
    """A search row with productsCount > 0 but no productId (live-site shape)."""
    return {
        "productsCount": 1,
        "productId": None,
        "storeProductId": 2366987,
        "storeName": "شركه فارما سكاي (الجيزه)",
        "retailPrice": 100,
        "salePrice": 80,
        "discountPercent": 20,
        "availableQuantity": 5,
    }


def test_missing_product_id_records_search_row_as_winner() -> None:
    bot, api = _bot(), _Api()
    record_api_match_only_store_metadata(bot, api, _Match(_row()))
    assert api.store_details_calls == []
    rows = list(captured_store_rows(bot))
    assert len(rows) == 1
    assert rows[0]["storeProductId"] == 2366987
    selections = list(captured_store_selections(bot))
    assert [store["storeProductId"] for store, _ in selections] == [2366987]
    assert [qty for _, qty in selections] == [0]


def test_with_product_id_still_fetches_store_details() -> None:
    bot, api = _bot(), _Api()
    data = _row() | {"productId": 555, "productsCount": 3}
    record_api_match_only_store_metadata(bot, api, _Match(data))
    assert api.store_details_calls == [555]
