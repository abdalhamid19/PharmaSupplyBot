"""Order item loading functions."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..core.manual_review_corrections import corrected_items_from_manual_review_csv
from ..core.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    filter_prevented_order_items,
    is_prevented_items_excel_path,
    load_prevented_items,
)
from ..core.utils.excel import (
    Item,
    load_items_from_excel,
    load_match_only_items_from_excel,
)


def load_order_items(app_config, args) -> Iterable[Item]:
    """Load and filter order items iteratively."""
    correction_items = manual_review_correction_items(args)
    if correction_items is not None:
        return correction_items
    require_order_excel(args)
    return load_regular_order_items(app_config, args)


def load_regular_order_items(app_config, args) -> Iterable[Item]:
    """Load regular order items from the configured Excel source."""
    excel_path = Path(args.excel)
    prevented_path = prevented_items_path(args)
    reject_prevented_excel_as_order_source(excel_path, prevented_path)
    has_prevented_filter = bool(prevented_path and prevented_path.is_file())
    items = load_items_for_order_mode(
        excel_path,
        app_config,
        args,
        has_prevented_filter,
    )
    if has_prevented_filter and prevented_path is not None:
        prevented_items = load_prevented_items(prevented_path)
        items = filter_prevented_order_items(items, prevented_items)
    return items


def manual_review_correction_items(args) -> Iterable[Item] | None:
    corrections = getattr(args, "from_manual_review_corrections", None)
    if not corrections:
        return None
    args.match_only = True
    return corrected_items_from_manual_review_csv(Path(corrections))


def require_order_excel(args) -> None:
    if not getattr(args, "excel", None):
        raise SystemExit("Provide --excel or --from-manual-review-corrections.")


def load_items_for_order_mode(
    excel_path: Path,
    app_config,
    args,
    has_prevented_filter: bool,
) -> Iterable[Item]:
    """Load items with a two-column catalog fallback in match-only mode."""
    limit = excel_load_limit(args, has_prevented_filter)
    if match_only(args):
        items = load_match_only_items_from_excel(
            excel_path, app_config.excel, limit=limit
        )
    else:
        items = load_items_from_excel(excel_path, app_config.excel, limit=limit)
    return slice_items(items, args)


def prevented_items_path(args) -> Path | None:
    """Return the configured prevented-items Excel path when one is enabled."""
    value = getattr(args, "prevented_items_excel", DEFAULT_PREVENTED_ITEMS_PATH)
    return Path(value) if value else None


def reject_prevented_excel_as_order_source(
    excel_path: Path, prevented_path: Path | None
) -> None:
    """Stop accidental ordering from the prevented-items management file."""
    if prevented_path and is_prevented_items_excel_path(excel_path, prevented_path):
        raise SystemExit("Order Excel cannot be the prevented-items Excel file.")
