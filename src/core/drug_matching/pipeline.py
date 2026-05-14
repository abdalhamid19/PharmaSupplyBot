"""Pipeline orchestrator - coordinates matching, verification, and output."""
import logging
from pathlib import Path

import pandas as pd

from .config import MatchingConfig, APIConfig, Paths, load_env
from .normalizer import parse_drug
from .indexer import DrugIndex
from .ai_steps import run_ai_verification, run_ai_search, run_ai_review
from .trace_log import MatchTraceLog

logger = logging.getLogger("pharmasupplybot.matching")

_RESULT_COLS = [
    "code", "drug_name", "matched_product_name_en",
    "matched_product_name_ar", "matched_store_product_id",
    "match_score", "verified", "match_method", "ai_confidence", "ai_review_confidence",
]


class MatchPipeline:
    """Full matching pipeline with optional AI verification."""

    __slots__ = (
        "_cfg", "_api_cfg", "_drugs_df", "_index",
        "_results", "_limit", "_start", "_end", "_trace",
    )

    def __init__(
        self,
        cfg: MatchingConfig | None = None,
        api_cfg: APIConfig | None = None,
        limit: int | None = None,
        start: int | None = None,
        end: int | None = None,
    ):
        load_env()
        self._cfg = cfg or MatchingConfig()
        self._api_cfg = api_cfg or APIConfig()
        self._limit = limit
        self._start = start
        self._end = end
        self._drugs_df: pd.DataFrame | None = None
        self._index: DrugIndex | None = None
        self._results: pd.DataFrame | None = None
        self._trace: MatchTraceLog | None = None

    # --- data loading ---

    def load_data(
        self, drugs_path: str | None = None,
        tawreed_path: str | None = None,
    ):
        """Load and prepare data sources."""
        paths = Paths()
        drugs_path = drugs_path or paths.drugs_csv
        tawreed_path = tawreed_path or paths.tawreed_csv
        drugs_raw = _read_table(drugs_path)
        drugs = drugs_raw.iloc[:, [0, 1]].copy()
        drugs.columns = ["code", "drug_name"]
        drugs["drug_price"] = (
            drugs_raw.iloc[:, 2] if drugs_raw.shape[1] > 2 else ""
        )
        tawreed = _read_table(tawreed_path)
        if self._start is not None or self._end is not None:
            s = self._start or 0
            e = self._end or len(drugs)
            drugs = drugs.iloc[s:e].reset_index(drop=True)
            logger.info(f"Slice applied: rows {s}-{e-1} ({len(drugs)} drugs)")
        if self._limit:
            drugs = drugs.head(self._limit)
            logger.info(f"Limit applied: processing {len(drugs)} drugs")
        self._drugs_df = drugs
        self._index = DrugIndex(tawreed, self._cfg)
        logger.info(
            f"Loaded {len(drugs)} drugs, "
            f"{self._index.size} tawreed products",
        )

    # --- Phase 1: algorithmic matching ---

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

    def _match_one(self, row, stats, row_index=""):
        """Match one drug, with trace if enabled."""
        drug_name = str(row.drug_name)
        price = getattr(row, "drug_price", None)
        if not self._trace or not self._trace.enabled:
            return self._index.best_match(drug_name, price)
        code = str(row.code)
        rec, score, method, trace = (
            self._index.best_match_detailed(drug_name, price)
        )
        parsed = parse_drug(drug_name)
        self._trace.log_normalization(
            code, drug_name, trace["norm"], trace["brand"],
            parsed.dosage_nums, parsed.form,
            row_index=row_index,
            components=self._trace.components_text(parsed),
        )
        for item in trace.get("candidates", []):
            self._trace.log_candidate_generated(
                code, drug_name, trace["norm"], trace["brand"],
                item["idx"], self._index, item["source"],
                item.get("rank", ""), item.get("score", ""),
                row_index=row_index,
            )
        for item in trace.get("score_breakdowns", []):
            self._trace.log_score_breakdown(
                code, drug_name, trace["norm"], trace["brand"],
                item, self._index, row_index=row_index,
            )
        self._trace.log_brand_lookup(
            code, drug_name, trace["norm"],
            trace["brand"], trace["brand_hits"],
            self._index, row_index=row_index,
        )
        for scorer_name, result in trace["fuzzy_steps"]:
            self._trace.log_fuzzy_step(
                code, drug_name, trace["norm"],
                trace["brand"], scorer_name, result,
                self._cfg.fuzzy_threshold, self._index,
                row_index=row_index,
            )
        for cidx, ok, reason in trace["component_checks"]:
            self._trace.log_component_check(
                code, drug_name, trace["norm"],
                trace["brand"], cidx, ok, reason,
                self._index, row_index=row_index,
            )
        match_name = rec["product_name_en"] if rec else None
        ai_eligible, ai_reason = self._ai_eligibility(
            rec, score, method, trace["norm"],
        )
        self._trace.log_final(
            code, drug_name, trace["norm"],
            trace["brand"], match_name, score, method,
            ai_eligible, ai_reason, row_index=row_index,
        )
        return rec, score, method

    def _ai_eligibility(self, rec, score, method, norm):
        """Determine if this drug will go to AI and why."""
        if rec is None:
            if method in {"too_short", "invalid_name"}:
                return "none", f"{method} -> not eligible for AI"
            return "search", (
                "no_match -> eligible for AI search"
            )
        if score < self._cfg.ai_verify_threshold:
            return "verify", (
                f"score={round(score,1)} "
                f"< ai_threshold={self._cfg.ai_verify_threshold}"
                f" -> eligible for AI verify"
            )
        return "none", (
            f"score={round(score,1)} "
            f">= ai_threshold={self._cfg.ai_verify_threshold}"
            f" -> strong match, no AI needed"
        )

    def _make_row(self, row, rec, score, method, stats):
        code = str(row.code)
        drug_name = str(row.drug_name)
        drug_price = getattr(row, "drug_price", "")
        if rec is not None:
            key = "brand_index" if "brand" in method else "fuzzy"
            stats[key] += 1
            return {
                "code": code, "drug_name": drug_name,
                "matched_product_name_en": rec["product_name_en"],
                "matched_product_name_ar": rec["product_name_ar"],
                "matched_store_product_id": rec["store_product_id"],
                "match_score": round(score, 1),
                "verified": "algo_match",
                "match_method": method,
                "ai_confidence": "",
                "ai_review_confidence": "",
                "_drug_price": drug_price,
                "_matched_price": rec.get("price", ""),
            }
        stats["no_match"] += 1
        return {
            "code": code, "drug_name": drug_name,
            "matched_product_name_en": "",
            "matched_product_name_ar": "",
            "matched_store_product_id": "",
            "match_score": "", "verified": "",
            "match_method": method,
            "ai_confidence": "",
            "ai_review_confidence": "",
            "_drug_price": drug_price,
            "_matched_price": "",
        }

    def _log_match_counts(self):
        matched = self._results[
            self._results["matched_product_name_en"] != ""
        ]
        total = len(self._results)
        logger.info(
            f"  Matched: {len(matched)}, "
            f"Not matched: {total - len(matched)}",
        )

    # --- Phase 2 & 3: AI steps (delegated) ---

    async def run_ai_verification(self) -> pd.DataFrame:
        """AI verification of matches below threshold."""
        self._require_results()
        self._results = await run_ai_verification(
            self._results, self._index, self._cfg, self._api_cfg,
            trace=self._trace,
        )
        return self._results

    async def run_ai_search_unmatched(self) -> pd.DataFrame:
        """AI searches for matches among unmatched items."""
        self._require_results()
        self._results = await run_ai_search(
            self._results, self._index, self._cfg, self._api_cfg,
            trace=self._trace,
        )
        return self._results

    async def run_ai_review(self) -> pd.DataFrame:
        """AI review: second model cross-verifies low-confidence AI decisions."""
        self._require_results()
        self._results = await run_ai_review(
            self._results, self._index, self._cfg, self._api_cfg,
            trace=self._trace,
        )
        return self._results

    # --- save & stats ---

    _PROGRESS_FILE = "artifacts/matching/.progress"

    def save_progress(self):
        """Save current progress (last completed row index) for --resume."""
        import json
        from pathlib import Path
        if self._drugs_df is None:
            return
        total = len(self._drugs_df)
        start = self._start or 0
        end = self._end or (start + total)
        progress = {
            "last_end": end,
            "total_loaded": total,
            "start": start,
        }
        Path(self._PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(self._PROGRESS_FILE).write_text(json.dumps(progress))
        logger.debug(f"Progress saved: last_end={end}")

    @staticmethod
    def load_progress() -> dict | None:
        """Load progress from previous run for --resume."""
        import json
        from pathlib import Path
        p = Path(MatchPipeline._PROGRESS_FILE)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, output_path: str | None = None) -> str:
        """Save results to CSV."""
        if self._results is None:
            raise RuntimeError("No results to save")
        path = output_path or str(Paths().output_csv)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._public_results(self._results).to_csv(
            path, index=False, encoding="utf-8-sig",
        )
        logger.info(f"Saved to {path}")
        self.save_progress()
        if self._trace and self._trace.enabled:
            self._trace.save()
        return path

    def save_manual_review(self, output_path: str | None = None) -> str:
        """Save unmatched and uncertain rows for manual review."""
        self._require_results()
        path = output_path or str(Paths().output_csv).replace(
            ".csv", "_manual_review.csv",
        )
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        review = self._manual_review_rows().copy()
        review["manual_review_reason"] = review.apply(
            _manual_review_reason_column, axis=1,
        )
        review["manual_decision"] = ""
        review["manual_reason"] = ""
        review["correct_store_product_id"] = ""
        self._public_results(review).to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"Manual review CSV saved to {path}")
        return path

    @staticmethod
    def _public_results(results: pd.DataFrame) -> pd.DataFrame:
        """Drop internal helper columns before writing public CSV files."""
        return results.loc[:, [c for c in results.columns if not c.startswith("_")]]

    def _manual_review_rows(self):
        has_match = (
            self._results["matched_product_name_en"].notna()
            & (self._results["matched_product_name_en"] != "")
        )
        scores = pd.to_numeric(
            self._results["match_score"], errors="coerce",
        ).fillna(0)
        uncertain = has_match & (scores < self._cfg.ai_verify_threshold)
        component_review = (
            self._results["_ai_component_reason"].fillna("").astype(str) != ""
            if "_ai_component_reason" in self._results.columns
            else False
        )
        return self._results[(~has_match) | uncertain | component_review]

    def print_stats(self):
        """Print final statistics."""
        if self._results is None:
            return
        total = len(self._results)
        has_match = (
            self._results["matched_product_name_en"].notna()
            & (self._results["matched_product_name_en"] != "")
        )
        matched = self._results[has_match]
        not_matched = self._results[~has_match]
        logger.info("=" * 50)
        logger.info("FINAL RESULTS")
        logger.info("=" * 50)
        logger.info(f"Total drugs: {total}")
        logger.info(
            f"Matched: {len(matched)} "
            f"({len(matched)/total*100:.1f}%)",
        )
        logger.info(
            f"Not matched: {len(not_matched)} "
            f"({len(not_matched)/total*100:.1f}%)",
        )
        if len(matched) > 0:
            self._log_score_dist(matched)
        logger.info("Verification breakdown:")
        logger.info(
            self._results["verified"]
            .value_counts(dropna=False).to_string(),
        )
        logger.info("Method breakdown:")
        logger.info(
            self._results["match_method"]
            .value_counts(dropna=False).to_string(),
        )

    def _log_score_dist(self, matched):
        scores = pd.to_numeric(matched["match_score"], errors="coerce")
        logger.info("Score distribution:")
        for label, lo, hi in [
            ("100", 100, 101), ("95-99", 95, 100),
            ("90-94", 90, 95), ("80-89", 80, 90),
            ("70-79", 70, 80),
        ]:
            count = ((scores >= lo) & (scores < hi)).sum()
            logger.info(f"  {label}: {count}")
        logger.info(f"  <70: {(scores < 70).sum()}")

    # --- full pipeline ---

    async def run_full(
        self, drugs_path: str | None = None,
        tawreed_path: str | None = None,
        output_path: str | None = None,
        skip_ai: bool = False,
    ) -> pd.DataFrame:
        """Run the complete pipeline."""
        self.load_data(drugs_path, tawreed_path)
        self.run_matching()
        if not skip_ai:
            await self.run_ai_verification()
            await self.run_ai_search_unmatched()
            await self.run_ai_review()
        saved_path = self.save(output_path)
        self.save_manual_review(_manual_review_path(saved_path))
        self.print_stats()
        return self._results

    # --- guards ---

    def _require_data(self):
        if self._drugs_df is None or self._index is None:
            raise RuntimeError("Call load_data() first")

    def _require_results(self):
        if self._results is None:
            raise RuntimeError("Call run_matching() first")


def _read_table(path: str | Path) -> pd.DataFrame:
    """Read a CSV or Excel table as strings."""
    source_path = Path(path)
    if source_path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(source_path, dtype=str)
    return pd.read_csv(source_path, encoding="utf-8-sig", dtype=str)


def _manual_review_path(output_path: str) -> str:
    """Return a manual-review path next to the main output CSV."""
    path = Path(output_path)
    return str(path.with_name(f"{path.stem}_manual_review{path.suffix}"))


def _manual_review_reason_column(row: pd.Series) -> str:
    """Build a human-readable reason explaining why this row needs review."""
    parts: list[str] = []
    verified = str(row.get("verified", "") or "")
    has_match = bool(row.get("matched_product_name_en"))

    if not has_match:
        parts.append("no_match_found")
    elif verified == "ai_rejected":
        parts.append("ai_rejected_match")
    elif verified == "ai_review_rejected":
        parts.append("ai_review_rejected_match")
    elif verified in ("ai_confirmed", "ai_corrected", "ai_found"):
        parts.append("low_confidence_ai_match")
    else:
        score = pd.to_numeric(row.get("match_score", 0), errors="coerce")
        if pd.notna(score) and score < 90:
            parts.append(f"uncertain_score({score:.0f})")

    # Expose internal AI component reason if present
    component = str(row.get("_ai_component_reason", "") or "")
    if component and component.lower() not in {"", "nan", "ok"}:
        parts.append(f"component:{component}")

    return "; ".join(parts) if parts else "needs_review"
