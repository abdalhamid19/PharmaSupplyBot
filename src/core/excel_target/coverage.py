"""Explain offline Excel-target identity and compatibility coverage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.core.config.config_models import MatchingConfig
from src.core.utils.excel import Item

from .excel_target_matching import ExcelTargetMatcher
from .product_attributes import validate_product_compatibility


@dataclass(frozen=True)
class CoverageRecord:
    """One auditable coverage classification for an order item."""

    target_key: str
    source_file: str
    item_code: str
    item_name: str
    catalog_size: int
    candidate_count: int
    compatible_count: int
    identity_evidence_kind: str
    identity_evidence: str
    compatibility_status: str
    compatibility_rejection: str
    coverage_category: str
    candidate_codes: str

    def to_row(self) -> dict[str, str | int]:
        """Return stable CSV/JSON-compatible fields."""
        return {
            "target_key": self.target_key,
            "source_file": self.source_file,
            "item_code": self.item_code,
            "item_name": self.item_name,
            "catalog_size": self.catalog_size,
            "candidate_count": self.candidate_count,
            "compatible_count": self.compatible_count,
            "identity_evidence_kind": self.identity_evidence_kind,
            "identity_evidence": self.identity_evidence,
            "compatibility_status": self.compatibility_status,
            "compatibility_rejection": self.compatibility_rejection,
            "coverage_category": self.coverage_category,
            "candidate_codes": self.candidate_codes,
        }


def build_coverage_records(
    matcher: ExcelTargetMatcher,
    items: Iterable[Item],
    _config: MatchingConfig,
) -> list[CoverageRecord]:
    """Classify each item using the matcher's already-built identity index.

    ``_config`` is accepted to keep the report seam aligned with the matcher
    and to make future policy-dependent coverage explicit. Coverage itself is
    deliberately based on identity and strict compatibility, not a second
    fuzzy matching implementation.
    """
    records: list[CoverageRecord] = []
    for item in items:
        identified = matcher.identity_index.identify(item.name)
        compatible = []
        rejected: list[str] = []
        for candidate in identified:
            result = validate_product_compatibility(item.name, candidate.product.name_ar)
            if result.accepted:
                compatible.append(candidate)
            else:
                rejected.append(result.rejection_reason)

        kinds = tuple(dict.fromkeys(c.evidence.kind for c in identified))
        details = tuple(dict.fromkeys(c.evidence.detail for c in identified))
        source_files = tuple(
            dict.fromkeys(c.product.source_file for c in identified if c.product.source_file)
        )
        if not identified:
            category = "identity_absent"
            status = "rejected"
            rejection = "identity evidence absent"
        elif compatible:
            category = "identity_compatible"
            status = "compatible"
            rejection = ""
        else:
            category = "identity_variant_rejected"
            status = "rejected"
            rejection = rejected[0] if rejected else "no compatible variant"

        records.append(
            CoverageRecord(
                target_key=matcher.target_key,
                source_file=";".join(source_files),
                item_code=str(item.code or ""),
                item_name=str(item.name or ""),
                catalog_size=len(matcher.catalog),
                candidate_count=len(identified),
                compatible_count=len(compatible),
                identity_evidence_kind=";".join(kinds),
                identity_evidence="; ".join(details),
                compatibility_status=status,
                compatibility_rejection=rejection,
                coverage_category=category,
                candidate_codes=";".join(c.product.code for c in identified),
            )
        )
    return records


__all__ = ["CoverageRecord", "build_coverage_records"]
