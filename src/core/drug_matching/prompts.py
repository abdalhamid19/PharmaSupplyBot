"""Prompt loading and rendering helpers for AI matching steps."""

from pathlib import Path
from string import Template

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

_SYSTEM_FALLBACK = """You are a pharmaceutical product matching expert.
Return JSON only and reject unsafe drug product mismatches."""

_VERIFY_FALLBACK = """Verify this drug match:

DRUG A (from inventory): $drug_a
DRUG B (from tawreed): $drug_b$drug_b_ar_line

Rules:
1. Concentration policy: You MUST REJECT the match if the requested drug has a 
   specific concentration (e.g., 5%) but the candidate lacks it, OR if they 
   have different concentrations. Only accept omitting concentration if the 
   drug universally has only one standard concentration.
2. Variant policy: You MUST REJECT if one is a specific variant/brand qualifier 
   (e.g., CARE, MACRO, COLLEDGE) and the other is a different variant or lacks it. 

Return JSON:
{"decision": "accept|reject", "is_correct": true/false", "reason": "brief reason", 
 "confidence": 0.0-1.0, "hard_conflicts": [], "matched_fields": [], 
 "mismatched_fields": []}"""

_SEARCH_FALLBACK = """Given this drug from inventory: "$drug_name"

Choose the correct candidate or 0 if none are correct.

Rules:
1. Concentration policy: You MUST REJECT the match if the requested drug has a 
   specific concentration (e.g., 5%) but the candidate lacks it, OR if they 
   have different concentrations. Only accept omitting concentration if the 
   drug universally has only one standard concentration.
2. Variant policy: You MUST REJECT if one is a specific variant/brand qualifier 
   (e.g., CARE, MACRO, COLLEDGE) and the other is a different variant or lacks it. 

Candidates:
$candidates_text

Return JSON:
{"decision": "accept|reject", "best_index": 0, "reason": "brief reason", 
 "confidence": 0.0, "hard_conflicts": [], "matched_fields": [], 
 "mismatched_fields": []}"""

_REVIEW_FALLBACK = """Review this AI decision about a drug match:

DRUG A (from inventory): $drug_a
DRUG B (from tawreed): $drug_b$drug_b_ar_line

First AI decided: $first_decision_text
First AI confidence: $first_confidence
First AI reason: $first_reason

Return JSON:
{"decision": "agree|disagree", "agree": true/false, "reason": "brief reason", "confidence": 0.0-1.0, "hard_conflicts": [], "matched_fields": [], "mismatched_fields": []}"""

_FRESH_REVIEW_FALLBACK = """The first AI model was unavailable.
Verify this match from scratch.

DRUG A (from inventory): $drug_a
DRUG B (from tawreed): $drug_b$drug_b_ar_line

Rules:
1. Concentration policy: You MUST REJECT the match if the requested drug has a 
   specific concentration (e.g., 5%) but the candidate lacks it, OR if they 
   have different concentrations. Only accept omitting concentration if the 
   drug universally has only one standard concentration.
2. Variant policy: You MUST REJECT if one is a specific variant/brand qualifier 
   (e.g., CARE, MACRO, COLLEDGE) and the other is a different variant or lacks it. 

Return JSON:
{"decision": "accept|reject", "is_correct": true/false", "reason": "brief reason", 
 "confidence": 0.0-1.0, "hard_conflicts": [], "matched_fields": [], 
 "mismatched_fields": []}"""


def _load(name: str, fallback: str) -> str:
    path = _PROMPT_DIR / name
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return fallback
    return text or fallback


def render_prompt(template: str, **values) -> str:
    """Render a prompt template with the provided values using safe substitution."""
    clean = {k: "" if v is None else str(v) for k, v in values.items()}
    return Template(template).safe_substitute(clean)


SYSTEM_PROMPT = _load("system.md", _SYSTEM_FALLBACK)
VERIFY_PROMPT = _load("verify_user.md", _VERIFY_FALLBACK)
SEARCH_PROMPT = _load("search_user.md", _SEARCH_FALLBACK)
REVIEW_PROMPT = _load("review_user.md", _REVIEW_FALLBACK)
FRESH_REVIEW_PROMPT = _load("fresh_review_user.md", _FRESH_REVIEW_FALLBACK)
