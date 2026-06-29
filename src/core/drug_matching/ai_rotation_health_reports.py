"""Report writing and loading logic for AI rotation health checks."""

import csv
import json
import time
from datetime import datetime
from pathlib import Path

from .ai_health import OUT_DIR


def write_rotation_reports(rows: list[dict]) -> tuple[Path, Path]:
    """Write rotation health test results to CSV and JSON files."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUT_DIR / f"ai_rotation_test_{stamp}.csv"
    json_path = OUT_DIR / f"ai_rotation_test_{stamp}.json"
    if not rows:
        rows = [{"provider": "", "model": "", "ok": False}]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return csv_path, json_path


def load_latest_rotation_health(max_age_s: float) -> list[dict]:
    """Load the most recent rotation health report within max_age_s seconds."""
    if max_age_s <= 0 or not OUT_DIR.exists():
        return []
    paths = sorted(OUT_DIR.glob("ai_rotation_test_*.json"), reverse=True)
    now = time.time()
    for path in paths:
        if now - path.stat().st_mtime > max_age_s:
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []
