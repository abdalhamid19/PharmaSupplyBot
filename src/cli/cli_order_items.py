"""Order item loading, filtering, and running logic."""

from __future__ import annotations

import csv
import itertools
from pathlib import Path
from typing import Iterable

from ..core.artifact_run import current_artifact_run
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
from ..tawreed.tawreed_match_only import MATCH_ONLY_SUMMARY_LABEL


# ============ Summary Functions ============


def summary_label(args) -> str:
    """Return the canonical summary label for the requested order mode."""
    if bool(getattr(args, "match_only", False)):
        return MATCH_ONLY_SUMMARY_LABEL
    return "order_item_summary"


def processed_summary_item_keys(
    profile_key: str, summary_label_value: str = "order_item_summary"
) -> set[tuple[str, str]]:
    """Return item keys already written to the active profile summary."""
    summary_path = latest_summary_path(profile_key, summary_label_value)
    if summary_path is None:
        return set()
    with summary_path.open("r", encoding="utf-8", newline="") as summary_file:
        reader = csv.DictReader(summary_file)
        return {
            item_key(row.get("item_code", ""), row.get("item_name", ""))
            for row in reader
        }


def latest_summary_path(profile_key: str, summary_label_value: str) -> Path | None:
    """Return the newest summary path from active, command, or legacy layouts."""
    active = current_artifact_run()
    paths: list[Path] = []
    if active:
        paths.extend(active.directory.glob(f"{summary_label_value}*.csv"))
    paths.extend(Path("artifacts/order").glob(f"{profile_key}/*/{summary_label_value}*.csv"))
    paths.append(Path("artifacts") / profile_key / f"{summary_label_value}.csv")
    paths.extend(Path("artifacts/legacy").glob(f"{profile_key}/*/{summary_label_value}*.csv"))
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def item_key(code: object, name: object) -> tuple[str, str]:
    """Return a stable key for matching Excel items to summary rows."""
    normalized_code = str(code or "").strip().lower()
    normalized_name = str(name or "").strip().lower()
    if normalized_code in {"", "nan", "none"}:
        normalized_code = ""
    return normalized_code, normalized_name


# ============ Filtering Functions ============


def slice_items(items: Iterable[Item], args) -> Iterable[Item]:
    """Apply start/end item slicing to the item iterable."""
    start_item = max(1, getattr(args, "start_item", 1))
    end_item = getattr(args, "end_item", 0)

    if start_item > 1:
        items = itertools.islice(items, start_item - 1, None)

    if end_item >= start_item:
        slice_limit = end_item - start_item + 1
        items = itertools.islice(items, slice_limit)

    return items


def excel_load_limit(args, has_prevented_filter: bool) -> int:
    """Return the safe Excel read limit before profile-level filters run."""
    if bool(getattr(args, "resume", False)) or has_prevented_filter:
        return 0
    if getattr(args, "start_item", 1) > 1 or getattr(args, "end_item", 0) > 0:
        return 0
    return order_item_limit(args)


def prepared_order_items(
    profile_key: str, items: Iterable[Item], args
) -> Iterable[Item]:
    """Yield one profile's remaining order items after session and resume checks."""
    from .cli_shared import require_state_file
    require_state_file(profile_key)
    if not bool(getattr(args, "resume", False)):
        yield from items
        return
    processed_keys = processed_summary_item_keys(profile_key, summary_label(args))
    for item in items:
        if item_key(item.code, item.name) not in processed_keys:
            yield item


def limited_order_items(items: Iterable[Item], args) -> Iterable[Item]:
    """Apply the per-run item limit after prevented/resume filters."""
    limit = order_item_limit(args)
    if limit <= 0:
        return items
    return itertools.islice(items, limit)


def order_item_limit(args) -> int:
    """Return the requested order item processing limit."""
    return int(getattr(args, "limit", 0) or 0)


def match_only(args) -> bool:
    """Return whether this order run should only evaluate product matches."""
    return bool(getattr(args, "match_only", False))


def ensure_non_empty_items(
    profile_key: str,
    items: Iterable[Item],
) -> Iterable[Item] | None:
    """Return an iterable that is guaranteed to yield at least one item, else None."""
    _, probe_iter = itertools.tee(items)
    try:
        first_item = next(probe_iter)
    except StopIteration:
        print(f"[{profile_key}] No remaining items to process.")
        return None
    return itertools.chain([first_item], probe_iter)


# ============ Loading Functions ============


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
    """Load items from manual review corrections CSV if requested."""
    corrections = getattr(args, "from_manual_review_corrections", None)
    if not corrections:
        return None
    args.match_only = True
    return corrected_items_from_manual_review_csv(Path(corrections))


def require_order_excel(args) -> None:
    """Validate that an Excel file was provided for order processing."""
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


# ============ Running Functions ============


def run_profile_items(
    app_config,
    profile_key: str,
    bot,
    items: Iterable[Item],
    args,
) -> None:
    """Run one profile through the requested order mode."""
    from .cli_order import run_profile_order, run_profile_match_only

    if match_only(args):
        run_profile_match_only(app_config.base_url, profile_key, bot, items)
        return
    run_profile_order(app_config.base_url, profile_key, bot, items)


# ============ Bot Options ============


def order_bot_options(args) -> dict[str, object]:
    """Extract bot options from CLI arguments."""
    from .cli_order import order_ai_settings
    stop_flag = getattr(args, "stop_flag", None)
    return {
        "debug_browser": bool(getattr(args, "debug_browser", False)),
        "stop_flag_path": Path(stop_flag) if stop_flag else None,
        "fast_search": bool(getattr(args, "fast_search", False)),
        "match_only": match_only(args),
        "order_ai_settings": order_ai_settings(args),
        "execution_mode": str(getattr(args, "execution_mode", "auto")),
        "matching_risk_policy": str(getattr(args, "matching_risk_policy", "safe")),
        "flagged_match_action": str(
            getattr(args, "flagged_match_action", "manual-review-only")
        ),
    }


__all__ = [
    # Summary
    "summary_label",
    "processed_summary_item_keys",
    "latest_summary_path",
    "item_key",
    # Filtering
    "slice_items",
    "excel_load_limit",
    "prepared_order_items",
    "limited_order_items",
    "order_item_limit",
    "match_only",
    "ensure_non_empty_items",
    # Loading
    "load_order_items",
    "load_regular_order_items",
    "manual_review_correction_items",
    "require_order_excel",
    "load_items_for_order_mode",
    "prevented_items_path",
    "reject_prevented_excel_as_order_source",
    # Running
    "run_profile_items",
    # Options
    "order_bot_options",
]
