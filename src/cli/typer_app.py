"""Typer + Rich CLI application for PharmaSupplyBot.

Five subcommands (registered incrementally in Tasks 6-10):
``auth``, ``order``, ``remove-cart``, ``export-products``, ``match-products``.

Each subcommand is a thin adapter that:

1. Calls :func:`src.cli.cli_runner.ns_from_ctx` to build an
   ``argparse.Namespace`` from the parsed Typer context.
2. Loads the config and applies presets / defaults.
3. Dispatches to the registered command in :mod:`src.cli.registry`.

The hand-rolled ``argparse`` parsers under ``src/cli/parsers/`` will
be removed in Task 14 once all subcommands are wired through here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer
from typer import Context

# Importing cli_commands has the side-effect of populating the command registry.
from src.cli import cli_commands  # noqa: F401
from src.cli.cli_runner import ns_from_ctx
from src.cli.cli_config import apply_preset, inject_defaults
from src.cli.logging_setup import LoggingConfig, configure_logging
from src.cli.presenter import FormatFlags
from src.cli.registry import get_command
from src.core.config.config import load_config
from src.core.errors import PharmaSupplyError


logger = logging.getLogger(__name__)


app = typer.Typer(
    name="pharmabot",
    help="Tawreed authentication, ordering, and exports CLI.",
    rich_markup_mode="rich",
    add_completion=False,  # we ship our own via `show-completion`
    no_args_is_help=True,
)


# ─────────────────────────── Global options ───────────────────────────


VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _validate_log_level(value: str) -> str:
    """Callback for ``--log-level``: reject unknown values with exit 2."""
    upper = value.upper()
    if upper not in VALID_LOG_LEVELS:
        raise typer.BadParameter(
            f"Invalid value: {value!r}. Choose from {', '.join(VALID_LOG_LEVELS)}."
        )
    return upper


@app.callback()
def _root(
    ctx: Context,
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        envvar="PHARMABOT_LOG_LEVEL",
        callback=_validate_log_level,
        help="Minimum log level emitted to console (DEBUG/INFO/WARNING/ERROR/CRITICAL).",
    ),
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress non-error console output."
    ),
    json_logs: bool = typer.Option(
        False,
        "--json-log-records",
        help="Emit log records as JSON (one object per line). Renamed from --json-logs.",
    ),
    rich_logs: bool = typer.Option(
        False,
        "--rich-logs",
        help="Route console log records through RichHandler for colourised output.",
    ),
) -> None:
    """Global logging + output options applied before any subcommand runs."""
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level
    ctx.obj["quiet"] = quiet
    ctx.obj["json_logs"] = json_logs
    ctx.obj["rich_logs"] = rich_logs


# ─────────────────────────── Hidden: shell-completion ──────────────────


@app.command("show-completion", hidden=True)
def show_completion(
    shell: str = typer.Argument(
        ..., help="Target shell: bash, zsh, or fish."
    )
) -> None:
    """Emit a shell-completion script for the given shell."""
    from typer.completion import get_completion_script

    if shell not in ("bash", "zsh", "fish"):
        typer.echo(
            f"Unknown shell '{shell}'. Supported: bash, zsh, fish.",
            err=True,
        )
        raise typer.Exit(5)
    # ``complete_var`` is the env var name read by the shell script.
    # Typer's convention: ``_TYPER_COMPLETE`` for bash/zsh, ``_FISH_COMPLETE`` for fish.
    complete_var = "_FISH_COMPLETE" if shell == "fish" else "_TYPER_COMPLETE"
    script = get_completion_script(
        shell=shell, prog_name="pharmabot", complete_var=complete_var
    )
    typer.echo(script)


# ─────────────────────────── Generic subcommand wrapper ────────────────


def _run_registered(ctx: Context, cmd_name: str) -> int:
    """Common entry-point for every subcommand.

    Sequence:
    1. Configure logging from the top-level options.
    2. Build a flat ``argparse.Namespace`` from the Typer context.
    3. Apply user-config precedence: preset < defaults < CLI args.
    4. Load :class:`AppConfig` and dispatch to the registered handler.

    Any :class:`PharmaSupplyError` is mapped to its ``exit_code`` and
    reported on stderr; anything else becomes exit code 99.
    """
    obj = ctx.obj or {}

    # 1. Logging (idempotent — safe to call multiple times).
    configure_logging(
        LoggingConfig(
            level=obj.get("log_level", "INFO"),
            quiet=bool(obj.get("quiet", False)),
            json_logs=bool(obj.get("json_logs", False)),
            rich_logs=bool(obj.get("rich_logs", False)),
        )
    )

    # 2. Materialise the legacy Namespace.
    ns = ns_from_ctx(ctx, cmd=cmd_name)
    ns._typer_defaults = _collect_defaults(ctx)

    # 3. Apply user-config precedence (CLI > preset > defaults).
    ns = apply_preset(None, ns, getattr(ns, "preset", None))  # type: ignore[arg-type]
    ns = inject_defaults(None, ns)  # type: ignore[arg-type]

    # 4. Load config + dispatch (full wrap so PharmaSupplyError always logs).
    fmt = FormatFlags.resolve(explicit="json" if obj.get("json_logs") else None)
    try:
        config_path = Path(getattr(ns, "config", "config.yaml"))
        app_config = load_config(config_path)
        logger.debug(
            "dispatching command",
            extra={"cmd": cmd_name, "config": str(config_path)},
        )
        command = get_command(cmd_name)
        return command(app_config, ns)
    except PharmaSupplyError as exc:
        logger.error(
            "command failed: %s",
            exc.message,
            extra={"exit_code": exc.exit_code, "profile": exc.profile},
        )
        if exc.hint:
            logger.warning("hint: %s", exc.hint)
        # In JSON-logs mode, the logger.error call already produced a
        # structured record; skip the duplicate human-format echo so the
        # stderr stream stays pure JSON for CI consumers.
        if not fmt.json:
            typer.echo(f"{exc}", err=True)
        raise typer.Exit(exc.exit_code)
    except Exception:
        logger.exception("unhandled exception in command %s", cmd_name)
        raise typer.Exit(99)


def _collect_defaults(ctx: Context) -> dict[str, Any]:
    """Snapshot the declared parameter defaults for ``_was_passed`` to consult."""
    defaults: dict[str, Any] = {}
    cmd = ctx.command
    if cmd is None:
        return defaults
    for param in cmd.params:
        name = getattr(param, "name", None)
        if name is not None:
            defaults[name] = param.default
    return defaults


# ─────────────────────────── One stub subcommand (auth) ────────────────


@app.command("auth")
def auth_cmd(
    ctx: Context,
    config: str = typer.Option(
        "state/config.yaml", "--config", "-c", help="Path to config.yaml."
    ),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Profile key."),
    all_profiles: bool = typer.Option(False, "--all-profiles", help="Run for all profiles."),
    preset: str | None = typer.Option(None, "--preset", help="User-config preset name."),
    headless: bool = typer.Option(False, "--headless", help="Run headless login."),
    wait_seconds: int = typer.Option(600, "--wait-seconds", help="Browser wait time (s)."),
) -> None:
    """Authenticate and persist session state for the selected profiles."""
    raise typer.Exit(_run_registered(ctx, "auth"))


@app.command("export-products")
def export_products_cmd(
    ctx: Context,
    config: str = typer.Option(
        "state/config.yaml", "--config", "-c", help="Path to config.yaml."
    ),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Profile key."),
    all_profiles: bool = typer.Option(False, "--all-profiles", help="Run for all profiles."),
    preset: str | None = typer.Option(None, "--preset", help="User-config preset name."),
    output_dir: str = typer.Option(
        "artifacts/{profile}", "--output-dir",
        help="Output directory; {profile} is replaced with the profile key.",
    ),
    stem: str = typer.Option(
        "tawreed_products", "--stem", help="Output filename without extension."
    ),
    page_size: int = typer.Option(100, "--page-size", help="Tawreed API page size."),
    limit: int = typer.Option(0, "--limit", "-n", help="Max rows to export (0 = all)."),
    debug_browser: bool = typer.Option(
        False, "--debug-browser", help="Open a visible browser for this run."
    ),
    format: str | None = typer.Option(
        None, "--format",
        help="Output format: human (default, TTY-only), json, or plain.",
    ),
) -> None:
    """Export all Tawreed store products to CSV, XLSX, and TXT."""
    raise typer.Exit(_run_registered(ctx, "export-products"))


@app.command("match-products")
def match_products_cmd(
    ctx: Context,
    config: str = typer.Option(
        "state/config.yaml", "--config", "-c", help="Path to config.yaml."
    ),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Profile key."),
    all_profiles: bool = typer.Option(False, "--all-profiles", help="Run for all profiles."),
    preset: str | None = typer.Option(None, "--preset", help="User-config preset name."),
    excel: str = typer.Option(..., "--excel", "-x", help="Inventory Excel/CSV file."),
    tawreed_csv: str | None = typer.Option(
        None, "--tawreed-csv", help="Tawreed products CSV path."
    ),
    output: str | None = typer.Option(None, "--output", help="Output CSV path."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Limit items."),
    start: int | None = typer.Option(None, "--start", help="Start item index."),
    end: int | None = typer.Option(None, "--end", help="End item index."),
    resume: bool = typer.Option(False, "--resume", help="Resume from saved state."),
    trace: bool = typer.Option(False, "--trace", help="Trace mode."),
    no_ai: bool = typer.Option(False, "--no-ai", help="Disable AI matching."),
    threshold: int = typer.Option(80, "--threshold", help="Score threshold."),
    ai_threshold: float = typer.Option(90.0, "--ai-threshold", help="AI score threshold."),
    ai_verify_policy: str = typer.Option(
        "score", "--ai-verify-policy",
        help="AI verify policy: score, fuzzy, all-non-exact, all.",
    ),
    ai_search_policy: str = typer.Option(
        "review-candidates", "--ai-search-policy",
        help="AI search policy: safe, review-candidates, expanded, aggressive.",
    ),
    provider: str | None = typer.Option(None, "--provider", help="AI provider."),
    model: str | None = typer.Option(None, "--model", help="AI model."),
    api_key: str | None = typer.Option(None, "--api-key", help="AI API key."),
    review_model: str | None = typer.Option(None, "--review-model", help="AI review model."),
    concurrency: int | None = typer.Option(None, "--concurrency", help="AI concurrency."),
    ai_search_limit: int | None = typer.Option(
        None, "--ai-search-limit", help="Limit AI search results."
    ),
    no_ai_preflight: bool = typer.Option(
        False, "--no-ai-preflight", help="Skip AI preflight check."
    ),
    rotation_preflight_policy: str = typer.Option(
        "smart", "--rotation-preflight-policy", help="API-rotation preflight policy."
    ),
    format: str | None = typer.Option(
        None, "--format",
        help="Output format: human (default, TTY-only), json, or plain.",
    ),
) -> None:
    """Match an inventory Excel/CSV file against exported Tawreed products."""
    raise typer.Exit(_run_registered(ctx, "match-products"))


@app.command("remove-cart")
def remove_cart_cmd(
    ctx: Context,
    config: str = typer.Option(
        "state/config.yaml", "--config", "-c", help="Path to config.yaml."
    ),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Profile key."),
    all_profiles: bool = typer.Option(False, "--all-profiles", help="Run for all profiles."),
    preset: str | None = typer.Option(None, "--preset", help="User-config preset name."),
    excel: str | None = typer.Option(
        None, "--excel", "-x", help="Path to cart-removal Excel file."
    ),
    debug_browser: bool = typer.Option(
        False, "--debug-browser", help="Open a visible browser for this run."
    ),
    stop_flag: str | None = typer.Option(
        None, "--stop-flag", help="Stop-request flag file path."
    ),
    execution_mode: str = typer.Option(
        "auto", "--execution-mode",
        help="Execution backend: auto, api, or browser.",
    ),
    item_workers: int | None = typer.Option(
        None, "--item-workers", help="Parallel item workers per profile."
    ),
    from_manual_review: str | None = typer.Option(
        None, "--from-manual-review", help="Manual-review CSV path."
    ),
    manual_review_scope: str = typer.Option(
        "current-run", "--manual-review-scope",
        help="Manual-review scope: current-run or saved-decisions.",
    ),
    manual_decision: str = typer.Option(
        "not_matching", "--manual-decision", help="Manual decision filter."
    ),
    format: str | None = typer.Option(
        None, "--format",
        help="Output format: human (default, TTY-only), json, or plain.",
    ),
) -> None:
    """Remove matching products from Tawreed carts."""
    raise typer.Exit(_run_registered(ctx, "remove-cart"))


@app.command("order")
def order_cmd(
    ctx: Context,
    config: str = typer.Option(
        "state/config.yaml", "--config", "-c", help="Path to config.yaml."
    ),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Profile key."),
    all_profiles: bool = typer.Option(False, "--all-profiles", help="Run for all profiles."),
    preset: str | None = typer.Option(None, "--preset", help="User-config preset name."),
    excel: str | None = typer.Option(
        None, "--excel", "-x",
        help="Path to order Excel file, usually under data/input/order_items/.",
    ),
    # Runtime
    limit: int = typer.Option(0, "--limit", "-n", help="Limit items (0 = no limit)."),
    debug_browser: bool = typer.Option(
        False, "--debug-browser", help="Open a visible browser for this run."
    ),
    max_workers: int | None = typer.Option(
        None, "--max-workers", help="Max parallel profiles (0 = unlimited)."
    ),
    start_item: int = typer.Option(
        1, "--start-item", help="Start processing from this item number."
    ),
    end_item: int = typer.Option(
        0, "--end-item", help="Stop after this item number (0 = end of sheet)."
    ),
    resume: bool = typer.Option(
        False, "--resume", help="Skip items in the active summary CSV."
    ),
    stop_flag: str | None = typer.Option(
        None, "--stop-flag", help="Stop-request flag file path."
    ),
    fast_search: bool = typer.Option(
        False, "--fast-search", help="Stop after the first acceptable match."
    ),
    match_only: bool = typer.Option(
        False, "--match-only", help="Only run matching; never add to cart."
    ),
    execution_mode: str = typer.Option(
        "auto", "--execution-mode",
        help="Execution backend: auto, api, or browser.",
    ),
    item_workers: int | None = typer.Option(
        None, "--item-workers", help="Parallel item workers per profile."
    ),
    # Risk
    matching_risk_policy: str = typer.Option(
        "safe", "--matching-risk-policy",
        help="Matching risk policy: safe or aggressive.",
    ),
    flagged_match_action: str = typer.Option(
        "manual-review-only", "--flagged-match-action",
        help="Action for flagged matches: manual-review-only or add-to-cart.",
    ),
    # AI
    ai: bool = typer.Option(False, "--ai", help="Enable active AI matching."),
    provider: str | None = typer.Option(None, "--provider", help="AI provider."),
    model: str | None = typer.Option(None, "--model", help="AI model."),
    api_key: str | None = typer.Option(None, "--api-key", help="AI API key."),
    review_model: str | None = typer.Option(None, "--review-model", help="AI review model."),
    concurrency: int | None = typer.Option(None, "--concurrency", help="AI concurrency."),
    ai_verify_policy: str = typer.Option(
        "score", "--ai-verify-policy",
        help="AI verify policy: score, fuzzy, all-non-exact, all.",
    ),
    ai_search_policy: str = typer.Option(
        "review-candidates", "--ai-search-policy",
        help="AI search policy: safe, review-candidates, expanded, aggressive.",
    ),
    ai_accept_confidence: float = typer.Option(
        0.9, "--ai-accept-confidence", help="AI auto-accept confidence."
    ),
    ai_verify_soft_accept_confidence: float = typer.Option(
        0.8, "--ai-verify-soft-accept-confidence",
        help="AI soft-accept confidence for verify policy.",
    ),
    ai_review_threshold: float = typer.Option(
        0.95, "--ai-review-threshold", help="Threshold to flag for manual review."
    ),
    no_ai_preflight: bool = typer.Option(
        False, "--no-ai-preflight", help="Skip AI preflight check."
    ),
    rotation_preflight_policy: str = typer.Option(
        "smart", "--rotation-preflight-policy", help="API-rotation preflight policy."
    ),
    # Filter
    warehouse_mode: str | None = typer.Option(
        None, "--warehouse-mode",
        help="Warehouse selection override: first_available, max_available, max_discount.",
    ),
    min_discount_percent: float | None = typer.Option(
        None, "--min-discount-percent",
        help="Only stores with discount ≥ this percent.",
    ),
    prevented_items_excel: str = typer.Option(
        "data/input/prevented_items/drugprevented.xlsx",
        "--prevented-items-excel",
        help="Path to XLSX of items that must not be ordered.",
    ),
    # Manual review
    from_manual_review_corrections: str | None = typer.Option(
        None, "--from-manual-review-corrections",
        help="Manual-review CSV with corrected rows to search match-only.",
    ),
    # Format
    format: str | None = typer.Option(
        None, "--format",
        help="Output format: human (default, TTY-only), json, or plain.",
    ),
) -> None:
    """Create orders from Excel (no human interaction)."""
    raise typer.Exit(_run_registered(ctx, "order"))


# Re-export for downstream imports
__all__ = ["app"]
