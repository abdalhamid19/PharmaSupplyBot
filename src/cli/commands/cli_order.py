"""Main CLI command runner for Tawreed ordering workflows."""

from __future__ import annotations

import argparse
import concurrent.futures
import logging
from pathlib import Path

from src.core.artifact_run import artifact_run
from src.core.config.config_models import AppConfig, ProfileConfig
from src.core.utils.excel import Item
from src.tawreed.tawreed import TawreedBot
from ..cli_shared import build_bot
from .cli_order_items import order_bot_options
from .cli_order_excel_target import (
    load_target_catalogs,
    run_excel_target_match_only_multi,
    selected_excel_target_configs,
)
from ..registry import register

logger = logging.getLogger(__name__)


# ============ Configuration ============


def apply_order_overrides(app_config: AppConfig, args: argparse.Namespace) -> None:
    """Apply optional per-run order settings to the loaded application config."""
    warehouse_mode = getattr(args, "warehouse_mode", None)
    if warehouse_mode:
        app_config.warehouse_strategy["mode"] = str(warehouse_mode)
    min_discount_percent = getattr(args, "min_discount_percent", None)
    if min_discount_percent is not None:
        app_config.warehouse_strategy["min_discount_percent"] = float(
            min_discount_percent
        )


def resolve_max_workers(
    app_config: AppConfig, args: argparse.Namespace, profile_count: int
) -> int:
    """Return the final concurrency limit for this run."""
    limit = getattr(args, "max_workers", None)
    if limit is None:
        limit = app_config.runtime.max_workers
    if limit <= 0:
        return profile_count
    return min(limit, profile_count)


def order_bot(
    app_config: AppConfig,
    profile_key: str,
    profile: ProfileConfig,
    args: argparse.Namespace,
) -> TawreedBot:
    """Build the bot used for one profile order run."""
    from .cli_order_items import order_bot_options
    return build_bot(
        app_config,
        profile_key,
        profile,
        **order_bot_options(args),
    )


# ============ Main Command Runner ============


@register("order")
def run_order_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Place orders from Excel for the selected profiles."""
    from ..cli_shared import (
        CommandTimer,
        format_duration,
        is_quiet,
        print_command_summary,
    )

    apply_order_overrides(app_config, args)

    profiles = app_config.profiles_to_run(
        profile=args.profile, all_profiles=args.all_profiles
    )
    if not profiles:
        profiles = []

    # Pre-allocate a single run id when an excel-target flow will run
    # alongside the Tawreed profiles so both sources land under the same
    # ``runs`` row. Without this, excel-target writes to its own auto-
    # generated run_key and never appears in the Tawreed run's
    # ``run_items`` / ``run_item_stores`` tables.
    shared_run_id: str | None = None
    selected_targets = selected_excel_target_configs(app_config, args)
    if selected_targets and profiles:
        from src.core.artifact_run import unique_run_id

        first_profile_key = profiles[0][0]
        shared_run_id = unique_run_id("order", first_profile_key)
        _open_shared_run_record(app_config, first_profile_key, shared_run_id, args)

    target_catalogs = (
        load_target_catalogs(selected_targets, app_config) if selected_targets else {}
    )

    target_items = _load_target_items(app_config, args)

    if selected_targets and target_items is not None:
        from src.core.artifact_run import current_artifact_run

        summary_path = (
            current_artifact_run().directory / "excel_target_summary.csv"
            if current_artifact_run()
            else Path("artifacts") / "excel_target_summary.csv"
        )
        excel_run_key = (
            f"{profiles[0][0]}/{shared_run_id}" if shared_run_id and profiles else None
        )
        excel_target_totals = run_excel_target_match_only_multi(
            app_config,
            selected_targets,
            target_catalogs,
            target_items,
            summary_path,
            run_key=excel_run_key,
            run_id=shared_run_id,
        )
    else:
        excel_target_totals = None

    timer = CommandTimer()
    run_directories: list[Path] = []
    processed = matched = flagged = 0
    with timer:
        from src.core.artifact_run import current_artifact_run

        execute_profiles(app_config, profiles, args, run_id=shared_run_id)

        # Cross-source winner reconciliation: when the Tawreed profile
        # and one or more Excel targets share a run_key, every flow
        # wrote its own ``is_winner=1`` row. Now we keep only the
        # cheapest purchase price as the unique winner so the Run
        # Results tab shows a single ✅ per item across sources.
        if shared_run_id and profiles:
            _reconcile_cross_source_winners(
                app_config, profiles[0][0], shared_run_id
            )

        # Snapshot: pull active run (if still set) + fall back to the
        # most recent run directory per profile from disk.
        active = current_artifact_run()
        if active and active.directory.exists():
            run_directories.append(active.directory)
        else:
            for profile_key, _ in profiles:
                run_directories.extend(_newest_run_dirs(profile_key))

        # Read counters from CSVs in THIS run's directory only.
        # We only count ``order_item_summary_*.csv`` — that file has
        # one row per INPUT item, which is what the operator means
        # by "processed". The ``match_only_summary_*.csv`` file has
        # one row per CANDIDATE (many candidates per item can be recorded),
        # so we deliberately exclude it to avoid inflating
        # the counter.
        for d in run_directories:
            for path in d.glob("order_item_summary_*.csv"):
                p, m, f = _count_from_summary_csvs([path])
                processed += p
                matched += m
                flagged += f

    # The "summary" field shows the first run's directory (or the
    # active one if available) so the operator can `ls` / open the
    # artifacts without guessing.
    primary_dir = run_directories[0] if run_directories else None

    summary_payload = {
        "processed": processed,
        "matched": matched,
        "flagged": flagged,
        "duration": format_duration(timer.seconds),
        "summary": primary_dir,
    }
    if excel_target_totals:
        summary_payload["excel_targets"] = excel_target_totals

    print_command_summary(
        "order",
        summary_payload,
        success=True,
        quiet=is_quiet(args),
    )
    return 0


def _reconcile_cross_source_winners(
    app_config: AppConfig, profile_key: str, run_id: str
) -> None:
    """Keep the cheapest offering store as the unique winner per item.

    The Tawreed and excel-target flows each write their own winner
    flag on the rows they produce. When both flows land under the
    same ``run_key`` an item can end up with two ``is_winner=1`` rows
    (one per source). This pass resets every ``is_winner`` to 0 and
    then flips the single cheapest row back to 1, so the Run Results
    tab shows exactly one ✅ per item regardless of source.

    Items with no rows at all, or rows with a NULL ``purchase_price``,
    fall back to the highest ``discount_percent`` so a 100% discount
    catalog row still wins over an empty Tawreed snapshot.
    """
    import sqlite3

    from src.core.database.order_runs_paths import default_order_runs_db
    from src.core.database.order_runs_store import OrderRunsStore

    database = getattr(app_config, "database", None)
    options = database.persistence_options() if database else {}
    db_path = options.get("path") or default_order_runs_db()
    run_key = f"{profile_key}/{run_id}"
    try:
        # Touch the store so any pending migration runs.
        OrderRunsStore(db_path)
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "update run_item_stores set is_winner = 0 where run_key = ?",
                (run_key,),
            )
            conn.execute(
                """
                update run_item_stores
                   set is_winner = 1
                 where run_key = ?
                   and rowid in (
                     select rowid from run_item_stores ris
                      where ris.run_key = ?
                        and ris.item_key = run_item_stores.item_key
                      order by
                        case when ris.purchase_price is null
                             then 1 else 0 end asc,
                        ris.purchase_price asc,
                        ris.discount_percent desc
                      limit 1
                   )
                """,
                (run_key, run_key),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        logger.debug(
            "cross-source winner reconciliation failed",
            extra={"run_key": run_key},
            exc_info=True,
        )


def _open_shared_run_record(
    app_config: AppConfig,
    profile_key: str,
    run_id: str,
    args: argparse.Namespace,
) -> None:
    """Pre-open the ``runs`` row that excel-target and Tawreed will share.

    The row is upserted, so the Tawreed ``open_order_run_record`` call that
    runs later will simply refresh the same row with the live mode/exec
    metadata. Without this pre-open, the excel-target flow would either
    write under its own auto-generated run_key (separate row in the DB)
    or fail the ``run_items`` foreign key when no run_key is supplied.
    """
    from .cli_order_run_record import order_run_options
    from src.core.ordering.order_run_persistence import open_run_record

    database = getattr(app_config, "database", None)
    options = database.persistence_options() if database else {}
    run_options = order_run_options(app_config, args, str(Path("artifacts") / "order" / profile_key / run_id))
    open_run_record(profile_key, run_id, run_options, options)


def _load_target_items(
    app_config: AppConfig, args: argparse.Namespace
) -> list[Item] | None:
    """Load items from the configured Excel when Excel targets are selected.

    Excel-target runs reuse the existing shortage Excel format (code/name/qty).
    When ``--excel`` is missing and no manual-review-corrections path is set,
    the Excel-target flow is skipped (the Tawreed profiles will still run).
    """
    if not getattr(args, "excel", None):
        return None
    from .cli_order_items import load_regular_order_items

    try:
        items = list(load_regular_order_items(app_config, args))
    except Exception as exc:
        logger.warning("excel target item load failed: %s", exc)
        return None
    return items


def _newest_run_dirs(profile_key: str) -> list[Path]:
    """Return the most recent run directories under
    ``artifacts/order/<profile>/**/`` (one per timestamp).
    """
    base = Path("artifacts") / "order" / profile_key
    if not base.exists():
        base = Path("artifacts") / profile_key
    if not base.exists():
        return []
    dirs = [d for d in base.iterdir() if d.is_dir()]
    # Sort by directory name (which is the timestamped run_id) — newest last.
    dirs.sort(key=lambda d: d.name, reverse=True)
    return [dirs[0]] if dirs else []


def _count_from_summary_csvs(paths: list[Path]) -> tuple[int, int, int]:
    """Return ``(processed, matched, flagged)`` totals across CSVs.

    Reads each CSV's ``status`` and ``manual_review_required`` columns
    if present. Returns ``(0, 0, 0)`` when no CSVs are readable so
    the caller still gets a clean summary block.

    Status values we recognise (from src/tawreed/order/tawreed_order_summary.py):
      * "matched-only"   — we found a candidate, did not add to cart
      * "added-to-cart"  — successful end-to-end placement
      * "no-results"     — no candidate matched the query
      * "not-orderable"  — candidate found but can't be ordered
      * "failed"         — errored mid-flow
      * "manual-review"  — requires human review (counted as flagged)

    The ``matched`` total includes both ``matched-only`` and
    ``added-to-cart`` since both indicate a successful match
    (whether or not it was placed). The ``flagged`` total is rows
    whose ``manual_review_required`` column is truthy.
    """
    if not paths:
        return 0, 0, 0
    total = matched = flagged = 0
    try:
        import csv as _csv

        for path in paths:
            with path.open("r", encoding="utf-8", newline="") as fh:
                reader = _csv.DictReader(fh)
                for row in reader:
                    total += 1
                    status = str(row.get("status", "")).strip()
                    if status in ("matched-only", "added-to-cart"):
                        matched += 1
                    mr = str(row.get("manual_review_required", "")).strip().lower()
                    if mr in ("true", "1", "yes"):
                        flagged += 1
    except (OSError, KeyError, ValueError):
        return 0, 0, 0
    return total, matched, flagged


def execute_profiles(
    app_config: AppConfig,
    profiles: list[tuple[str, ProfileConfig]],
    args: argparse.Namespace,
    run_id: str | None = None,
) -> None:
    """Run the selected profiles either sequentially or in parallel.

    ``run_id`` is threaded down to :func:`run_single_profile` so a
    pre-allocated artifact run id (computed by the caller to share the
    run with the excel-target flow) is used for every profile.
    """
    from .cli_order_execution import run_single_profile

    max_workers = resolve_max_workers(app_config, args, len(profiles))
    if max_workers <= 1:
        for profile_key, profile in profiles:
            run_single_profile(app_config, profile_key, profile, args, run_id=run_id)
        return

    run_parallel_profiles(app_config, profiles, args, max_workers, run_id=run_id)


def run_parallel_profiles(
    app_config: AppConfig,
    profiles: list[tuple[str, ProfileConfig]],
    args: argparse.Namespace,
    max_workers: int,
    run_id: str | None = None,
) -> None:
    """Submit profile-level order runs to the configured thread pool."""
    from .cli_order_execution import run_single_profile

    logger.info(
        "running profiles in parallel",
        extra={"profile_count": len(profiles), "max_workers": max_workers},
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(run_single_profile, app_config, pk, p, args, run_id=run_id)
            for pk, p in profiles
        ]
        concurrent.futures.wait(futures)


__all__ = [
    # Configuration
    "apply_order_overrides",
    "resolve_max_workers",
    "order_bot",
    # Main Command
    "run_order_command",
    "execute_profiles",
    "run_parallel_profiles",
]
