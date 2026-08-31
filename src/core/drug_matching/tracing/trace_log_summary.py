"""Summary writer for deterministic matching traces."""

from __future__ import annotations

import csv


class SummaryWriter:
    def __init__(self, parent_logger):
        self._parent = parent_logger

    def save_summary(self, path):
        rows = self._rows()
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["code", "drug_name", "final_status", "final_match", "primary_reason"])
            writer.writeheader()
            writer.writerows(rows)

    def _rows(self):
        grouped = {}
        for row in self._parent._rows:
            grouped.setdefault((row.get("drug_code", ""), row.get("drug_name", "")), []).append(row)
        result = []
        for (code, name), rows in grouped.items():
            final = next((row for row in reversed(rows) if row.get("step") == "final"), {})
            match = final.get("final_match", "")
            result.append({"code": code, "drug_name": name, "final_status": "matched" if match and match != "NONE" else "no_match", "final_match": match, "primary_reason": final.get("selection_reason", "")})
        return result


__all__ = ["SummaryWriter"]
