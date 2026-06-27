"""Index building logic for DrugIndex."""

from collections import defaultdict

import pandas as pd

from .config import MatchingConfig
from .normalizer import DrugComponents, normalize, parse_drug
from .pricing import parse_price


class IndexBuilder:
    """Handles building inverted indexes for DrugIndex."""

    def __init__(self, tawreed_df: pd.DataFrame, cfg: MatchingConfig | None = None):
        self._cfg = cfg or MatchingConfig()
        self._names_en = []
        self._names_ar = []
        self._ids = []
        self._norms = []
        self._parsed = []
        self._prices = []
        self._brand_index: dict[str, list[int]] = defaultdict(list)
        self._component_index: dict[tuple, list[int]] = defaultdict(list)
        self._prefix_index: dict[str, list[int]] = defaultdict(list)
        self._process_dataframe(tawreed_df)
        self._build_indexes()

    def _process_dataframe(self, tawreed_df: pd.DataFrame) -> None:
        """Process the input DataFrame into internal lists."""
        original_cols = list(tawreed_df.columns)
        df = tawreed_df.rename(
            columns={
                original_cols[0]: "product_name_ar",
                original_cols[1]: "product_name_en",
                original_cols[2]: "store_product_id",
            }
        )
        price_col = self._find_price_col(df, original_cols)
        self._names_en = df["product_name_en"].tolist()
        self._names_ar = df["product_name_ar"].tolist()
        self._ids = df["store_product_id"].astype(str).tolist()
        self._prices = (
            [self._parse_price(v) for v in df[price_col].tolist()]
            if price_col
            else [None] * len(df)
        )
        self._norms = [normalize(n) for n in self._names_en]
        self._parsed = [parse_drug(n) for n in self._names_en]

    def _build_indexes(self) -> None:
        """Build all inverted indexes."""
        self._build_brand_index()
        self._build_component_index()
        self._build_prefix_index()

    def _build_brand_index(self) -> None:
        """Build brand-based inverted index."""
        for i, parsed in enumerate(self._parsed):
            for brand in self._brand_keys(parsed):
                for plen in range(3, min(len(brand) + 1, 8)):
                    self._brand_index[brand[:plen]].append(i)

    def _build_component_index(self) -> None:
        """Build component-based inverted index."""
        for i, parsed in enumerate(self._parsed):
            for key in self._component_keys(parsed):
                self._component_index[key].append(i)

    def _build_prefix_index(self) -> None:
        """Build prefix-based inverted index for fuzzy matching."""
        prefix_len = self._cfg.fuzzy_prefix_len
        for i, norm in enumerate(self._norms):
            self._prefix_index[norm[:prefix_len]].append(i)

    @staticmethod
    def _brand_keys(parsed: DrugComponents) -> tuple[str, ...]:
        """Extract brand keys from parsed components."""
        import re
        keys = []
        for brand in (parsed.brand, *parsed.brand_variants):
            cleaned = re.sub(r"[^A-Z0-9]", "", brand)
            if len(cleaned) >= 3 and cleaned not in keys:
                keys.append(cleaned)
        return tuple(keys)

    def _component_keys(self, parsed: DrugComponents) -> list[tuple]:
        """Extract component keys for inverted index."""
        brands = self._brand_keys(parsed)
        if not brands:
            return []
        keys = []
        for brand in brands:
            keys.append(("brand", brand))
            if parsed.volume:
                keys.append(("brand_volume", brand, parsed.volume))
            if parsed.qty:
                keys.append(("brand_qty", brand, parsed.qty))
            if parsed.dosage_nums:
                keys.append(("brand_dosage", brand, parsed.dosage_nums))
            if parsed.flavor:
                keys.append(("brand_flavor", brand, parsed.flavor))
        return keys

    @staticmethod
    def _find_price_col(df: pd.DataFrame, original_cols: list[str]):
        """Find the price column in the DataFrame."""
        for col in df.columns:
            if str(col).strip().lower() in {
                "price",
                "product_price",
                "selling_price",
                "sale_price",
                "سعر",
            }:
                return col
        if len(original_cols) >= 5:
            return original_cols[4]
        return None

    @staticmethod
    def _parse_price(value) -> float | None:
        """Parse price value."""
        return parse_price(value)

    def get_indexes(self) -> tuple:
        """Return all built indexes for DrugIndex."""
        return (
            self._names_en,
            self._names_ar,
            self._ids,
            self._norms,
            self._parsed,
            self._prices,
            self._brand_index,
            self._component_index,
            self._prefix_index,
        )


__all__ = ["IndexBuilder"]
