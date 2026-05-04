from src.tawreed_strategy import choose_store_index


def test_choose_store_index_max_discount_prefers_highest_discount():
    stores = [
        {"availableQuantity": 2, "discountPercent": "10%"},
        {"availableQuantity": 5, "discountPercent": "5%"},
        {"availableQuantity": 3, "discountPercent": "0.15"},
    ]

    assert choose_store_index(stores, "max_discount", RuntimeError) == 2
