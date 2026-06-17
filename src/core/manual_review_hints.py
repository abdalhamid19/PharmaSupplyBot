"""Manual-review correction hints for future matching runs."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManualReviewHint:
    """A human-approved item to Tawreed store product mapping."""

    item_code: str
    item_name: str
    store_product_id: str
    manual_reason: str = ""


def load_manual_review_hints(path: str | Path) -> dict[tuple[str, str], ManualReviewHint]:
    """Load review hints from CSV or JSON, keyed by item code/name."""
    source = Path(path)
    if source.suffix.lower() == ".json":
        rows = json.loads(source.read_text(encoding="utf-8"))
    else:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    hints = [hint for row in rows if (hint := _hint_from_row(row))]
    return {hint_key(hint.item_code, hint.item_name): hint for hint in hints}


def export_manual_review_hints(input_csv: str | Path, output_json: str | Path) -> int:
    """Write approved manual-review hints to JSON and return the count."""
    hints = list(load_manual_review_hints(input_csv).values())
    payload = [asdict(hint) for hint in hints]
    target = Path(output_json)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(payload)


def hint_key(item_code: str, item_name: str) -> tuple[str, str]:
    """Return the stable lookup key for an order item."""
    return (_clean_code(item_code).upper(), _clean(item_name).upper())


def _hint_from_row(row: dict) -> ManualReviewHint | None:
    store_product_id = _clean(row.get("correct_store_product_id", ""))
    if not store_product_id:
        return None
    decision = _clean(row.get("manual_decision", "")).lower()
    if decision and decision not in {"accept", "accepted", "correct", "approved"}:
        return None
    item_code = _clean(row.get("item_code", ""))
    item_name = _clean(row.get("item_name", ""))
    if not item_code and not item_name:
        return None
    return ManualReviewHint(
        item_code=item_code,
        item_name=item_name,
        store_product_id=store_product_id,
        manual_reason=_clean(row.get("manual_reason", "")),
    )


def _clean(value: object) -> str:
    text = " ".join(str(value or "").strip().split())
    return "" if text.lower() in {"nan", "none", "null"} else text


def _clean_code(value: object) -> str:
    """Return a stable item-code key for values loaded from Excel."""
    text = _clean(value)
    return text[:-2] if text.endswith(".0") else text
