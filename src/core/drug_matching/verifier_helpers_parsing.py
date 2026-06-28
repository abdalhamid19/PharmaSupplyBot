"""JSON parsing and extraction functions for AI verifier."""

from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict | None:
    """Extract JSON from model response, handling markdown code blocks and truncation."""
    if not isinstance(text, str) or not text:
        return None
    # Try direct parse
    if parsed := loads_json_object(text):
        return json_with_safe_defaults(parsed)
    # Try extracting from ```json ... ``` block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        if parsed := loads_json_object(m.group(1)):
            return json_with_safe_defaults(parsed)
    # Try finding first { ... } in text
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        if parsed := loads_json_object(m.group(0)):
            return json_with_safe_defaults(parsed)
    # Handle truncated JSON: find opening { and try to close it
    start = text.find("{")
    if start >= 0:
        fragment = text[start:]
        # Try adding closing braces
        for suffix in ["}", "\"}", "\"\n}"]:
            try:
                return json_with_safe_defaults(json.loads(fragment + suffix))
            except (json.JSONDecodeError, ValueError):
                continue
        # Last resort: extract key-value pairs with regex
        is_correct_m = re.search(r'"is_correct"\s*:\s*(true|false)', fragment, re.IGNORECASE)
        reason_m = re.search(r'"reason"\s*:\s*"([^"]*)"', fragment)
        confidence_m = re.search(r'"confidence"\s*:\s*([\d.]+)', fragment)
        if is_correct_m:
            return {
                "is_correct": is_correct_m.group(1).lower() == "true",
                "reason": reason_m.group(1) if reason_m else "",
                "confidence": float(confidence_m.group(1)) if confidence_m else 0.5,
            }
        decision_m = re.search(r'"decision"\s*:\s*"([^"]*)"', fragment)
        best_index_m = re.search(r'"best_index"\s*:\s*(\d+)', fragment)
        if decision_m or best_index_m:
            return {
                "decision": decision_m.group(1) if decision_m else "",
                "best_index": int(best_index_m.group(1)) if best_index_m else 0,
                "reason": reason_m.group(1) if reason_m else "",
                "confidence": float(confidence_m.group(1)) if confidence_m else 0.5,
            }
    return None


def json_with_safe_defaults(parsed: dict) -> dict:
    """Add conservative defaults when a repaired search response is incomplete."""
    if (
        ("decision" in parsed or "best_index" in parsed)
        and "confidence" not in parsed
    ):
        parsed["confidence"] = 0.5
    return parsed


def loads_json_object(text: str) -> dict | None:
    """Parse a JSON object after repairing common model formatting noise."""
    for candidate in (text, re.sub(r",\s*([}\]])", r"\1", text)):
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def infer_is_correct(text: str) -> bool:
    """Infer match correctness from text when JSON parsing fails."""
    lower = text.lower()
    # Strong reject signals
    for word in ["different brand", "not the same", "mismatch", "incorrect",
                 "wrong match", "different product", "different dosage",
                 "different form", "different quantity"]:
        if word in lower:
            return False
    # Strong accept signals
    for word in ["same product", "correct match", "identical", "is_correct",
                 "matching", "same brand", "same dosage"]:
        if word in lower:
            return True
    # Default: reject (safer for drug matching)
    return False


def api_error_code(status: int, text: str) -> str:
    lowered = text.lower()
    if status == 400 and (
        "failed_generation" in lowered
        or "failed to validate json" in lowered
        or '"code":"json_' in lowered
    ):
        return "json_generation_failed"
    return f"http_{status}"
