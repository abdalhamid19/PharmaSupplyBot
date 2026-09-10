"""JSONL persistence for top candidates during manual review."""

from __future__ import annotations

import json
from pathlib import Path

from .manual_review_candidates import ReviewCandidateOption
from .manual_review_hints import hint_key


def append_review_candidates(
    run_dir: Path, item_code: str, item_name: str, options: list[ReviewCandidateOption]
) -> None:
    """Append the item's top N candidates to the run's JSONL file."""
    code_key, name_key = hint_key(item_code, item_name)
    item_key = f"{code_key}::{name_key}"
    
    payload = {
        "item_key": item_key,
        "item_code": item_code,
        "item_name": item_name,
        "options": [opt.to_dict() for opt in options],
    }
    
    file_path = run_dir / f"manual_review_candidates_{run_dir.name}.jsonl"
    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_review_candidates(run_dir: Path) -> dict[str, list[ReviewCandidateOption]]:
    """Return candidates from every JSONL artifact in ``run_dir``.

    Older runs use one file named ``manual_review_candidates_<run>.jsonl``.
    Excel-target runs may emit one file per target, so the loader deliberately
    accepts the whole ``manual_review_candidates_*.jsonl`` family and merges
    records by item key.  Envelope provenance is copied onto options when an
    option does not already carry it.
    """
    files = sorted(run_dir.glob("manual_review_candidates_*.jsonl"))
    if not files:
        return {}

    results: dict[str, list[ReviewCandidateOption]] = {}
    seen: dict[str, set[tuple[str, ...]]] = {}
    for file_path in files:
        with file_path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # A partially written artifact should not hide candidates
                    # from other files in the same run.
                    continue
                item_key = str(data.get("item_key") or "").strip()
                if not item_key:
                    code_key, name_key = hint_key(
                        data.get("item_code", ""), data.get("item_name", "")
                    )
                    item_key = f"{code_key}::{name_key}"
                if not item_key or item_key == "::":
                    continue
                options: list[ReviewCandidateOption] = []
                for raw_option in data.get("options", []) or []:
                    if not isinstance(raw_option, dict):
                        continue
                    option_data = dict(raw_option)
                    _inherit_envelope_metadata(option_data, data)
                    try:
                        option = ReviewCandidateOption.from_dict(option_data)
                    except (TypeError, ValueError):
                        continue
                    options.append(option)

                bucket = results.setdefault(item_key, [])
                bucket_seen = seen.setdefault(item_key, set())
                for option in options:
                    identity = (
                        option.store_product_id,
                        option.name_en,
                        option.name_ar,
                        option.matching_source,
                        option.target_key,
                        option.source_file,
                        option.excel_target_row_key,
                    )
                    if identity in bucket_seen:
                        continue
                    bucket_seen.add(identity)
                    bucket.append(option)

    return results


def _inherit_envelope_metadata(option: dict, envelope: dict) -> None:
    """Copy record-level provenance onto an option without overwriting it."""
    aliases = {
        "matching_source": ("matching_source", "source_kind", "source"),
        "matching_source_label": ("matching_source_label", "source_label"),
        "target_key": ("target_key", "excel_target_key"),
        "source_file": ("source_file", "candidate_source_file"),
        "identity_evidence_kind": ("identity_evidence_kind",),
        "identity_evidence": ("identity_evidence",),
        "compatibility_status": ("compatibility_status",),
        "compatibility_rejection": (
            "compatibility_rejection",
            "rejection_reason",
        ),
    }
    for destination, keys in aliases.items():
        if option.get(destination):
            continue
        for key in keys:
            value = envelope.get(key)
            if value not in (None, ""):
                option[destination] = value
                break
