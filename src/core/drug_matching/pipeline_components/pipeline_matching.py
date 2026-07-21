"""Phase 1 algorithmic matching logic for the pipeline."""

from __future__ import annotations

import logging

import pandas as pd

from ..config import MatchingConfig
from ..indexing.indexer import DrugIndex
from ..tracing.trace_log import MatchTraceLog
from .pipeline_io import PipelineIO

logger = logging.getLogger(__name__)

_RESULT_COLS = [
    "code", "drug_name", "matched_product_name_en",
    "matched_product_name_ar", "matched_store_product_id",
    "match_score", "verified", "match_method", "ai_confidence", "ai_review_confidence",
]


class PipelineMatching:
    """Phase 1 algorithmic matching logic."""

    def __init__(self, cfg: MatchingConfig, index: DrugIndex, trace, io: PipelineIO):
        self._cfg = cfg
        self._index = index
        self._trace = trace
        self._io = io
        self._drugs_df: pd.DataFrame | None = None
        self._results: pd.DataFrame | None = None
        self._matching_engine = None

    def load_data(
        self, drugs_path: str | None = None,
        tawreed_path: str | None = None,
        limit: int | None = None,
        start: int | None = None,
        end: int | None = None,
    ):
        """Load and prepare data sources."""
        from ..config import Paths
        paths = Paths()
        drugs_path = drugs_path or paths.drugs_csv
        tawreed_path = tawreed_path or paths.tawreed_csv
        drugs_raw = self._io.read_table(drugs_path)
        drugs = drugs_raw.iloc[:, [0, 1]].copy()
        drugs.columns = ["code", "drug_name"]
        drugs["drug_price"] = (
            drugs_raw.iloc[:, 2] if drugs_raw.shape[1] > 2 else ""
        )
        tawreed = self._io.read_table(tawreed_path)
        if start is not None or end is not None:
            s = start or 0
            e = end or len(drugs)
            drugs = drugs.iloc[s:e].reset_index(drop=True)
            logger.info(f"Slice applied: rows {s}-{e-1} ({len(drugs)} drugs)")
        if limit:
            drugs = drugs.head(limit)
            logger.info(f"Limit applied: processing {len(drugs)} drugs")
        self._drugs_df = drugs
        logger.info(
            f"Loaded {len(drugs)} drugs, "
            f"{self._index.size} tawreed products",
        )

    def run_matching(self) -> pd.DataFrame:
        """Algorithmic matching using brand index + fuzzy search."""
        self._require_data()
        results = []
        stats = {"brand_index": 0, "fuzzy": 0, "no_match": 0}
        for row_index, row in enumerate(self._drugs_df.itertuples(index=False)):
            rec, score, method = self._match_one(row, stats, row_index)
            results.append(self._make_row(row, rec, score, method, stats))
        self._results = pd.DataFrame(results, columns=_RESULT_COLS if not results else None)
        # Allow mixed str/float in numeric-optional columns
        for col in ("match_score", "ai_confidence", "ai_review_confidence"):
            if col in self._results.columns:
                self._results[col] = self._results[col].astype(object)
        logger.info(f"Phase 1 done: {stats}")
        self._log_match_counts()
        return self._results

    def _log_match_counts(self):
        """Log matching statistics."""
        matched = self._results[
            self._results["matched_product_name_en"] != ""
        ]
        total = len(self._results)
        logger.info(
            f"  Matched: {len(matched)}, "
            f"Not matched: {total - len(matched)}",
        )

    def _require_data(self):
        if self._drugs_df is None:
            raise RuntimeError("Call load_data() first")

    def _match_one(self, row, stats, row_index):
        """Match one drug record."""
        rec, score, method = self._index.best_match(row.drug_name)
        if rec is not None:
            if method in ("component_index", "brand_index"):
                stats["brand_index"] += 1
            else:
                stats["fuzzy"] += 1
        else:
            stats["no_match"] += 1
        return rec, score, method

    def _make_row(self, row, rec, score, method, stats):
        """Build one result row."""
        if rec is None:
            return {
                "code": row.code,
                "drug_name": row.drug_name,
                "matched_product_name_en": "",
                "matched_product_name_ar": "",
                "matched_store_product_id": "",
                "match_score": 0.0,
                "verified": "",
                "match_method": method,
                "ai_confidence": "",
                "ai_review_confidence": "",
            }
        return {
            "code": row.code,
            "drug_name": row.drug_name,
            "matched_product_name_en": rec.get("productNameEn", ""),
            "matched_product_name_ar": rec.get("productName", ""),
            "matched_store_product_id": rec.get("storeProductId", ""),
            "match_score": score,
            "verified": "",
            "match_method": method,
            "ai_confidence": "",
            "ai_review_confidence": "",
        }


__all__ = [
    "_RESULT_COLS",
    "PipelineMatching",
]
