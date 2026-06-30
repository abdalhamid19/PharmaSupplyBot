"""Reporting functions for AI health checks."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import PROVIDERS
from .ai_health_test import AIKey, empty_result

OPENCODE_BASE_URL = PROVIDERS["opencode"]["base_url"]
OUT_DIR = Path("output/api_model_tests")


def healthy_combos(rows: list[dict[str, Any]]) -> tuple[tuple[str, str], ...]:
    """Extract healthy key/model combinations from test results."""
    combos = []
    seen = set()
    for row in rows:
        if not row.get("ok") or row.get("mode") != "json":
            continue
        combo = (str(row["key_masked"])[-6:], str(row["model"]))
        if combo not in seen:
            seen.add(combo)
            combos.append(combo)
    return tuple(combos)


def write_reports(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    """Write health check results to CSV and JSON files."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUT_DIR / f"opencode_model_test_{stamp}.csv"
    json_path = OUT_DIR / f"opencode_model_test_{stamp}.json"
    if not rows:
        rows = [empty_result(AIKey("", ""), "", "", OPENCODE_BASE_URL)]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return csv_path, json_path


__all__ = [
    "healthy_combos",
    "write_reports",
    "OUT_DIR",
]
