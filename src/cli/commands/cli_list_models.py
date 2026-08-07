"""CLI command runner to discover available AI models per provider (live /models).

Probes each configured provider's OpenAI-compatible ``/models`` endpoint
and reports the live catalog, plus which configured models have gone
missing remotely (retired / renamed).

Output honours the CLI's three-tier format: JSON / plain TSV / Rich table
(auto-detected from TTY unless ``--format`` is given).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from src.core.config.config_models import AppConfig
from src.core.drug_matching.ai.ai_model_discovery import discover_models
from ..presenter import FormatFlags, render_summary, render_table
from ..registry import register

__all__ = ["run_list_models_command"]


def _emit_table(rows: list[dict], columns: list[str], fmt: FormatFlags) -> None:
    """Render a table exactly once (Rich human-mode prints internally)."""
    if fmt.json or fmt.plain:
        sys.stdout.write(render_table(rows, columns, fmt) + "\n")
    else:
        render_table(rows, columns, fmt)  # human: console.print handles output


@register("list-models")
def run_list_models_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Probe live ``/models`` endpoints and list available models per provider."""
    provider = getattr(args, "provider", None)
    providers = (
        tuple(p.strip() for p in provider.split(",") if p.strip())
        if isinstance(provider, str) and provider.strip()
        else None
    )

    result = discover_models(
        providers,
        config_path=(
            Path(getattr(args, "config", None))
            if getattr(args, "config", None)
            else None
        ),
        timeout_s=float(getattr(args, "timeout", 20)),
    )

    fmt = FormatFlags.resolve(explicit=getattr(args, "format", None))
    rows: list[dict] = []
    for cat in result.catalogs:
        if cat.reachable:
            status = "OK"
        elif cat.http_status is not None:
            status = f"HTTP {cat.http_status}"
        else:
            status = cat.error_type or "ERR"

        rows.append(
            {
                "provider": cat.provider,
                "status": status,
                "remote_models": len(cat.models),
                "configured_models": len(cat.configured_models),
                "live_ok": sum(
                    1 for m in cat.models if m in set(cat.configured_models)
                ),
                "stale_configured": len(cat.missing_from_remote),
            }
        )

    _emit_table(
        rows,
        ["provider", "status", "remote_models", "configured_models", "live_ok", "stale_configured"],
        fmt,
    )

    # Detailed per-provider model listing.
    for cat in result.catalogs:
        if not cat.reachable:
            continue
        model_rows = [{"provider": cat.provider, "model": m} for m in cat.models]
        _emit_table(model_rows, ["provider", "model"], fmt)

    ok_providers = [c.provider for c in result.catalogs if c.reachable]
    summary = render_summary(
        "list-models",
        {
            "providers_reachable": len(ok_providers),
            "total_providers": len(result.catalogs),
            "providers": ", ".join(ok_providers) or "-",
        },
        fmt,
    )
    if fmt.json or fmt.plain:
        sys.stdout.write(summary + "\n")
    return 0
