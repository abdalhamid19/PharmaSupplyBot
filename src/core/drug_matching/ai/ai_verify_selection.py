"""Selection logic for AI verification."""

from __future__ import annotations

import pandas as pd

from .ai_verify_helpers import _FUZZY_VERIFY_METHODS


def _select_for_verification(results, cfg):
    """Select rows for AI verification based on policy."""
    matched = results[results["matched_product_name_en"] != ""].copy()
    scores = pd.to_numeric(matched["match_score"], errors="coerce")
    policy = getattr(cfg, "ai_verify_policy", "score")
    methods = matched["match_method"].fillna("")
    if policy == "all":
        selected = matched
    elif policy == "all-non-exact":
        selected = matched[
            ~((methods == "component_index") & (scores >= 100.0))
        ]
    elif policy == "fuzzy":
        selected = matched[
            (scores < cfg.ai_verify_threshold) |
            methods.isin(_FUZZY_VERIFY_METHODS)
        ]
    else:
        selected = matched[scores < cfg.ai_verify_threshold]
    if cfg.ai_verify_limit is not None:
        selected = selected.head(cfg.ai_verify_limit)
    return selected


def _build_verify_items(to_verify):
    """Build verification items from DataFrame rows."""
    return [
        (
            row["drug_name"],
            row["matched_product_name_en"],
            row.get("matched_product_name_ar", ""),
            idx,
            row.get("match_score", ""),
            row.get("match_method", ""),
            row.get("_drug_price", ""),
            row.get("_matched_price", ""),
        )
        for idx, row in to_verify.iterrows()
    ]


__all__ = ["_select_for_verification", "_build_verify_items"]
