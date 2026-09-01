"""Excel target source — secondary match surface beside Tawreed profiles."""

from .excel_target_loader import (
    TargetProduct,
    iter_target_candidates,
    load_target_catalog_from_excel,
)
from .excel_target_matching import (
    ExcelTargetMatch,
    find_best_match_in_target,
    first_accepted_match,
    load_target_catalog,
    match_item_against_all_targets,
)

__all__ = [
    "TargetProduct",
    "ExcelTargetMatch",
    "iter_target_candidates",
    "load_target_catalog_from_excel",
    "load_target_catalog",
    "find_best_match_in_target",
    "match_item_against_all_targets",
    "first_accepted_match",
]