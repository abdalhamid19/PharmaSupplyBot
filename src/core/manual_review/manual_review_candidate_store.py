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
    """Return all review candidate lists mapped by item_key."""
    file_path = run_dir / f"manual_review_candidates_{run_dir.name}.jsonl"
    if not file_path.exists():
        return {}
        
    results = {}
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            options = [ReviewCandidateOption.from_dict(opt) for opt in data["options"]]
            results[data["item_key"]] = options
            
    return results
