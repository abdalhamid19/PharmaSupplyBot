"""AI-powered match verification using Agent Router API."""
import asyncio
import json
import logging
import re
from typing import Any

import aiohttp

from .config import APIConfig
from .normalizer import parse_drug
from .pricing import format_price, price_context, price_delta_text
from .prompts import (
    FRESH_REVIEW_PROMPT,
    REVIEW_PROMPT,
    SEARCH_PROMPT,
    SYSTEM_PROMPT,
    VERIFY_PROMPT,
    render_prompt,
)

logger = logging.getLogger("pharmasupplybot.matching")

_TRANSIENT_COMBO_FAILURE_LIMIT = 2
_PERMANENT_PARSE_FAILURES = frozenset((
    "invalid_json",
    "null_content",
    "json_generation_failed",
))
# AI-reported conflicts that override is_correct=True → force reject.
_HARD_CONFLICT_REJECT = frozenset((
    "different_strength",
    "different_dosage",
    "different_active_ingredient",
    "different_concentration",
    "different_route",
))
# AI-reported conflicts that lower confidence but don't force reject.
_HARD_CONFLICT_PENALTY = frozenset((
    "different_form",
    "different_quantity",
    "different_volume",
    "different_brand",
    "different_flavor",
    "different_age_group",
    "different_pack_size",
))


def _coerce_best_index(value, max_index: int) -> tuple[int, bool]:
    """Return a safe candidate index and whether the source value was valid."""
    if isinstance(value, bool) or value is None:
        return 0, False
    if isinstance(value, int):
        idx = value
    elif isinstance(value, str) and value.strip().isdigit():
        idx = int(value.strip())
    else:
        return 0, False
    if 0 <= idx <= max_index:
        return idx, True
    return 0, False


def _api_error_code(status: int, text: str) -> str:
    lowered = text.lower()
    if status == 400 and (
        "failed_generation" in lowered
        or "failed to validate json" in lowered
        or '"code":"json_' in lowered
    ):
        return "json_generation_failed"
    return f"http_{status}"


def _extract_json(text: str) -> dict | None:
    """Extract JSON from model response, handling markdown code blocks and truncation."""
    if not isinstance(text, str) or not text:
        return None
    # Try direct parse
    if parsed := _loads_json_object(text):
        return _json_with_safe_defaults(parsed)
    # Try extracting from ```json ... ``` block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        if parsed := _loads_json_object(m.group(1)):
            return _json_with_safe_defaults(parsed)
    # Try finding first { ... } in text
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        if parsed := _loads_json_object(m.group(0)):
            return _json_with_safe_defaults(parsed)
    # Handle truncated JSON: find opening { and try to close it
    start = text.find("{")
    if start >= 0:
        fragment = text[start:]
        # Try adding closing braces
        for suffix in ["}", "\"}", "\"\n}"]:
            try:
                return _json_with_safe_defaults(json.loads(fragment + suffix))
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


def _json_with_safe_defaults(parsed: dict) -> dict:
    """Add conservative defaults when a repaired search response is incomplete."""
    if (
        ("decision" in parsed or "best_index" in parsed)
        and "confidence" not in parsed
    ):
        parsed["confidence"] = 0.5
    return parsed


def _loads_json_object(text: str) -> dict | None:
    """Parse a JSON object after repairing common model formatting noise."""
    for candidate in (text, re.sub(r",\s*([}\]])", r"\1", text)):
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _infer_is_correct(text: str) -> bool:
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


def _resolve_ai_conflicts(result: dict[str, Any]) -> dict[str, Any]:
    """Detect and resolve contradictions in AI response fields.

    1. If hard_conflicts contain a critical mismatch → force is_correct=False.
    2. If decision='reject' but is_correct=True → trust decision, set is_correct=False.
    3. If hard_conflicts contain non-critical items → cap confidence.
    """
    hard_lower = _hard_conflict_names(result)
    _apply_critical_conflicts(result, hard_lower)
    _apply_conflict_penalty(result, hard_lower)
    _apply_reject_decision_override(result)
    return result


def _hard_conflict_names(result: dict[str, Any]) -> set[str]:
    hard = result.get("hard_conflicts") or []
    if isinstance(hard, str):
        hard = [h.strip() for h in hard.split(",") if h.strip()]
    return {h.lower().replace(" ", "_") for h in hard}


def _apply_critical_conflicts(result: dict[str, Any], hard_lower: set[str]) -> None:
    critical = hard_lower & _HARD_CONFLICT_REJECT
    if critical and result.get("is_correct"):
        result["is_correct"] = False
        conflict_text = ", ".join(sorted(critical))
        reason = result.get("reason", "")
        result["reason"] = (
            f"hard_conflict_override({conflict_text}); {reason}"
            if reason else f"hard_conflict_override({conflict_text})"
        )
        result["confidence"] = min(result.get("confidence", 0.0), 0.55)


def _apply_conflict_penalty(result: dict[str, Any], hard_lower: set[str]) -> None:
    penalty = hard_lower & _HARD_CONFLICT_PENALTY
    if penalty and result.get("is_correct"):
        result["confidence"] = min(result.get("confidence", 0.0), 0.72)


def _apply_reject_decision_override(result: dict[str, Any]) -> None:
    decision = str(result.get("decision", "")).lower().strip()
    if decision == "reject" and result.get("is_correct"):
        result["is_correct"] = False
        reason = result.get("reason", "")
        result["reason"] = (
            f"decision_reject_override; {reason}" if reason
            else "decision_reject_override"
        )
        result["confidence"] = min(result.get("confidence", 0.0), 0.6)


def _fallback_from_unparseable_response(text: str, model: str) -> dict[str, Any]:
    return {
        "is_correct": False,
        "agree": False,
        "reason": f"invalid_json:{text[:180]}",
        "confidence": 0.4,
        "model_used": model,
        "parse_failed": True,
    }


def _route_from_norm(norm: str) -> str:
    words = set(norm.split())
    routes = set(words & {"IM", "IV", "SC"})
    if {"I", "M"} <= words:
        routes.add("IM")
    if {"I", "V"} <= words:
        routes.add("IV")
    if {"S", "C"} <= words:
        routes.add("SC")
    return "/".join(sorted(routes)) or "-"


def _component_context(name: str) -> str:
    c = parse_drug(name)
    return (
        f"normalized='{c.normalized}', brand='{c.brand}', "
        f"dosage={c.dosage_nums or '-'}, qty='{c.qty or '-'}', "
        f"volume='{c.volume or '-'}', weight='{c.weight or '-'}', "
        f"form='{c.form or '-'}', flavor='{c.flavor or '-'}', "
        f"class='{c.product_class}', "
        f"route='{_route_from_norm(c.normalized)}', "
        f"imported={'yes' if c.imported else 'no'}"
    )


def _format_candidate(
    position: int, candidate: tuple[dict, float, int],
    inventory_price=None,
) -> str:
    rec, score, _ = candidate[:3]
    review_reason = candidate[3] if len(candidate) > 3 else "ok"
    review_text = (
        "" if review_reason == "ok"
        else f"\n   rule_review: candidate entered AI review despite {review_reason}; accept only if the products are truly equivalent"
    )
    candidate_price = rec.get("price")
    price_text = (
        f", candidate_price={format_price(candidate_price)}, "
        f"price_delta={price_delta_text(inventory_price, candidate_price)}"
    )
    return (
        f"{position}. {rec['product_name_en']} / "
        f"{rec.get('product_name_ar', '')} "
        f"(score={score:.1f}{price_text})\n"
        f"   parsed: {_component_context(rec['product_name_en'])}"
        f"{review_text}"
    )


def _normalize_verify_item(
    item: tuple,
) -> tuple[str, str, str, int, str, str, object, object]:
    """Support old verify items plus optional score/method context."""
    if len(item) == 3:
        drug_a, drug_b, row_idx = item
        return drug_a, drug_b, "", row_idx, "", "", None, None
    if len(item) == 4:
        drug_a, drug_b, drug_b_ar, row_idx = item
        return drug_a, drug_b, drug_b_ar, row_idx, "", "", None, None
    if len(item) == 6:
        drug_a, drug_b, drug_b_ar, row_idx, score, method = item
        return drug_a, drug_b, drug_b_ar, row_idx, score, method, None, None
    drug_a, drug_b, drug_b_ar, row_idx = item[:4]
    score, method = item[4], item[5]
    inventory_price, candidate_price = item[6], item[7]
    return (
        drug_a, drug_b, drug_b_ar, row_idx, score, method,
        inventory_price, candidate_price,
    )


def _normalize_review_item(item: tuple) -> tuple:
    """Support review items with optional inventory/candidate prices."""
    if len(item) == 8:
        return (*item, None, None)
    return item


class AIVerifier:
    """Async AI verification client with rate limiting, batching, and key/model fallback."""

    __slots__ = (
        "_cfg", "_session", "_semaphore", "_fallback_log",
        "_failed_combos", "_combo_failures", "_rotation_cursors",
    )

    def __init__(self, cfg: APIConfig | None = None, max_concurrent: int = 5):
        self._cfg = cfg or APIConfig()
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._fallback_log: list[str] = []
        self._failed_combos: set[tuple[str, str]] = set()
        self._combo_failures: dict[tuple[str, str], int] = {}
        self._rotation_cursors: dict[str, int] = {}

    def get_fallback_log(self) -> str:
        """Return and clear the API failure log for trace reporting."""
        if not self._fallback_log:
            return ""
        log = "; ".join(self._fallback_log)
        self._fallback_log.clear()
        return log

    def _build_attempt_plan(self, model: str) -> list[tuple[str, str]]:
        """Build ordered list of (api_key, model) to try, skipping previously failed combos.
        Order: primary key + primary model → other keys + primary model → fallback models + all keys."""
        keys = self._cfg.api_keys if self._cfg.api_keys else (self._cfg.api_key,)
        models = [model] + list(self._cfg.fallback_models)
        healthy = set(self._cfg.healthy_combos or ())
        plan = []
        # Phase 1: try primary model with all keys
        for key in keys:
            combo = (key[-6:], models[0])
            if combo not in self._failed_combos and (not healthy or combo in healthy):
                plan.append((key, models[0]))
        # Phase 2: try each fallback model with all keys
        for mdl in models[1:]:
            for key in keys:
                combo = (key[-6:], mdl)
                if combo not in self._failed_combos and (not healthy or combo in healthy):
                    plan.append((key, mdl))
        return plan

    def _build_request_plan(self, model: str) -> list[dict[str, Any]]:
        if self._cfg.attempt_plan:
            return self._rotation_request_plan(model)
        return [
            {
                "provider": "default",
                "base_url": self._cfg.base_url,
                "key": key,
                "model": mdl,
            }
            for key, mdl in self._build_attempt_plan(model)
        ]

    def _rotation_request_plan(self, requested_model: str = "") -> list[dict[str, Any]]:
        attempts = self._rotation_attempts_for(requested_model)
        plan = []
        for tier in sorted({attempt.rotation_tier for attempt in attempts}):
            tier_attempts = [
                attempt for attempt in attempts
                if attempt.rotation_tier == tier
                and self._combo_key(
                    attempt.api_key, attempt.model, attempt.provider,
                ) not in self._failed_combos
            ]
            plan.extend(
                self._rotated_tier_plan(
                    tier_attempts, requested_model, tier,
                    advance=not plan,
                ),
            )
        return plan

    def _rotation_attempts_for(self, requested_model: str = ""):
        attempts = self._cfg.attempt_plan
        if requested_model == "rotation" and self._cfg.review_attempt_plan:
            return self._strong_enough_review_attempts(
                self._cfg.review_attempt_plan,
            )
        elif requested_model and requested_model != self._cfg.model:
            matching = tuple(
                attempt for attempt in attempts
                if attempt.model == requested_model
            )
            if matching:
                return self._strong_enough_review_attempts(matching)
        return attempts

    def _strong_enough_review_attempts(self, attempts):
        primary = self._primary_rotation_attempt()
        if primary is None:
            return tuple(attempts)
        primary_strength = self._attempt_strength(primary)
        return tuple(
            attempt for attempt in attempts
            if self._attempt_strength(attempt) <= primary_strength
        )

    def _primary_rotation_attempt(self):
        for attempt in self._cfg.attempt_plan:
            if attempt.model == self._cfg.model:
                return attempt
        return self._cfg.attempt_plan[0] if self._cfg.attempt_plan else None

    @staticmethod
    def _attempt_strength(attempt) -> tuple[int, int]:
        return attempt.rotation_tier, attempt.quality_rank

    def _rotated_tier_plan(
        self, attempts, requested_model: str, tier: int, *, advance: bool,
    ) -> list[dict[str, Any]]:
        if not attempts:
            return []
        key = self._rotation_cursor_key(requested_model, tier)
        start = self._rotation_cursors.get(key, 0) % len(attempts)
        if advance:
            self._rotation_cursors[key] = (start + 1) % len(attempts)
        indexed = list(enumerate(attempts))
        ordered = indexed[start:] + indexed[:start]
        return [
            self._rotation_plan_item(attempt, key, position, len(attempts))
            for position, attempt in ordered
        ]

    def _rotation_plan_item(
        self, attempt, cursor_key: str, position: int, count: int,
    ) -> dict[str, Any]:
        return {
            "provider": attempt.provider,
            "base_url": attempt.base_url,
            "key": attempt.api_key,
            "model": attempt.model,
            "rotation_cursor_key": cursor_key,
            "rotation_position": position,
            "rotation_count": count,
            "rotation_tier": attempt.rotation_tier,
        }

    def _rotation_cursor_key(self, requested_model: str, tier: int) -> str:
        if requested_model == "rotation" and self._cfg.review_attempt_plan:
            scope = "review"
        elif requested_model and requested_model != self._cfg.model:
            scope = f"model:{requested_model}"
        else:
            scope = "primary"
        return f"{scope}:tier:{tier}"

    def _record_rotation_used(self, item: dict[str, Any]) -> None:
        key = item.get("rotation_cursor_key")
        position = item.get("rotation_position")
        count = item.get("rotation_count")
        if key is None or position is None or not count:
            return
        self._rotation_cursors[str(key)] = (int(position) + 1) % int(count)

    def _record_combo_failure(
        self, key: str, model: str, reason: str,
        *, permanent: bool = False, provider: str = "",
    ) -> bool:
        """Track failures and disable noisy key/model combos for this run."""
        combo = self._combo_key(key, model, provider)
        if permanent:
            self._failed_combos.add(combo)
            return True
        count = self._combo_failures.get(combo, 0) + 1
        self._combo_failures[combo] = count
        if count >= _TRANSIENT_COMBO_FAILURE_LIMIT:
            self._failed_combos.add(combo)
            return True
        return False

    def _log_combo_failure(
        self, key: str, model: str, reason: str, detail: str = "",
        provider: str = "",
    ) -> None:
        detail_text = f": {detail[:160]}" if detail else ""
        provider_text = f" provider={provider}" if provider else ""
        log_msg = (
            f"{reason}{detail_text} with{provider_text} "
            f"model={model} key=...{key[-6:]}"
        )
        self._fallback_log.append(log_msg)
        logger.warning("  ⚠ %s, trying next...", log_msg)

    @staticmethod
    def _combo_key(key: str, model: str, provider: str = ""):
        if provider:
            return provider, key[-6:], model
        return key[-6:], model

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "HTTP-Referer": "https://pharmasupplybot.local",
                "X-Title": "MediCompare Drug Matcher",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def _call_api(self, payload: dict, max_retries: int = 2) -> dict[str, Any] | None:
        """Make an API call with key+model fallback.
        Tries each (key, model) combination from the attempt plan.
        Returns parsed result dict or None if all attempts fail."""
        if not self._cfg.api_key:
            return None
        close_session = False
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://pharmasupplybot.local",
                    "X-Title": "MediCompare Drug Matcher",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            )
            close_session = True
        model = payload.get("model", self._cfg.model)
        plan = self._build_request_plan(model)
        attempts = []
        last_unparseable: tuple[str, str] | None = None

        try:
            for plan_idx, item in enumerate(plan):
                key = item["key"]
                mdl = item["model"]
                base_url = item["base_url"]
                provider = item["provider"]
                combo_key = self._combo_key(key, mdl, provider)
                if combo_key in self._failed_combos:
                    continue
                payload["model"] = mdl
                headers = dict(self._session.headers)
                headers["Authorization"] = f"Bearer {key}"

                for attempt in range(max_retries + 1):
                    async with self._semaphore:
                        if combo_key in self._failed_combos:
                            break
                        try:
                            async with self._session.post(
                                f"{base_url}/chat/completions",
                                json=payload,
                                headers=headers,
                            ) as resp:
                                if resp.status == 429:
                                    retry_after = resp.headers.get("Retry-After", "")
                                    disabled = self._record_combo_failure(
                                        key, mdl, "rate_limited",
                                        permanent=bool(retry_after),
                                        provider=provider,
                                    )
                                    attempts.append({
                                        "attempt": attempt + 1,
                                        "provider": provider,
                                        "key_suffix": key[-6:],
                                        "model": mdl,
                                        "status": resp.status,
                                        "fallback_used": plan_idx > 0,
                                        "decision": "disabled" if disabled else "failed",
                                        "error_stage": "api",
                                        "error_code": "rate_limited",
                                        "reason": (
                                            f"429 retry_after="
                                            f"{retry_after or '10'}"
                                        ),
                                    })
                                    self._log_combo_failure(
                                        key, mdl, "Rate limited",
                                        attempts[-1]["reason"],
                                        provider=provider,
                                    )
                                    break
                                if resp.status != 200:
                                    text = await resp.text()
                                    error_code = _api_error_code(resp.status, text)
                                    disabled = self._record_combo_failure(
                                        key, mdl, error_code,
                                        permanent=(
                                            resp.status in (401, 403)
                                            or error_code == "json_generation_failed"
                                        ),
                                        provider=provider,
                                    )
                                    attempts.append({
                                        "attempt": attempt + 1,
                                        "provider": provider,
                                        "key_suffix": key[-6:],
                                        "model": mdl,
                                        "status": resp.status,
                                        "fallback_used": plan_idx > 0,
                                        "decision": "disabled" if disabled else "failed",
                                        "error_stage": "api",
                                        "error_code": error_code,
                                        "reason": text[:200],
                                    })
                                    log_reason = (
                                        "JSON generation failed"
                                        if error_code == "json_generation_failed"
                                        else f"API error {resp.status}"
                                    )
                                    self._log_combo_failure(
                                        key, mdl, log_reason, text,
                                        provider=provider,
                                    )
                                    break  # try next (key, model) combo
                                data = await resp.json()
                                content = data["choices"][0]["message"].get("content")
                                content_text = content if isinstance(content, str) else ""
                                result = _extract_json(content)
                                if result is None:
                                    error_code = "null_content" if content is None else "invalid_json"
                                    disabled = self._record_combo_failure(
                                        key, mdl, error_code,
                                        permanent=error_code in _PERMANENT_PARSE_FAILURES,
                                        provider=provider,
                                    )
                                    attempts.append({
                                        "attempt": attempt + 1,
                                        "provider": provider,
                                        "key_suffix": key[-6:],
                                        "model": mdl,
                                        "status": 200,
                                        "fallback_used": plan_idx > 0,
                                        "decision": "disabled" if disabled else "parse_failed",
                                        "error_stage": "ai_parse",
                                        "error_code": error_code,
                                        "parse_failed": True,
                                        "reason": content_text[:200],
                                    })
                                    last_unparseable = (content_text, mdl)
                                    logger.warning(
                                        "  ⚠ %s from model=%s",
                                        error_code, mdl,
                                    )
                                    break
                                attempts.append({
                                    "attempt": attempt + 1,
                                    "provider": provider,
                                    "key_suffix": key[-6:],
                                    "model": mdl,
                                    "status": 200,
                                    "fallback_used": plan_idx > 0,
                                    "decision": "success",
                                    "reason": "parsed_json",
                                })
                                self._combo_failures.pop(
                                    self._combo_key(key, mdl, provider), None,
                                )
                                confidence = float(result.get("confidence", 0.0))
                                if confidence == 0.0:
                                    is_correct = bool(result.get("is_correct", False))
                                    confidence = 0.7 if is_correct else 0.6
                                self._record_rotation_used(item)
                                parsed_result = {
                                    "is_correct": bool(result.get("is_correct", False)),
                                    "agree": bool(result.get("agree", True)),
                                    "reason": str(result.get("reason", "")),
                                    "confidence": confidence,
                                    "model_used": mdl,
                                    "provider_used": provider,
                                    "decision": str(result.get("decision", "")),
                                    "hard_conflicts": result.get("hard_conflicts", []),
                                    "matched_fields": result.get("matched_fields", []),
                                    "mismatched_fields": result.get("mismatched_fields", []),
                                    "_raw": result,
                                    "_api_attempts": attempts,
                                }
                                return _resolve_ai_conflicts(parsed_result)
                        except Exception as e:
                            disabled = self._record_combo_failure(
                                key, mdl, type(e).__name__,
                                provider=provider,
                            )
                            attempts.append({
                                "attempt": attempt + 1,
                                "provider": provider,
                                "key_suffix": key[-6:],
                                "model": mdl,
                                "status": "exception",
                                "fallback_used": plan_idx > 0,
                                "decision": "disabled" if disabled else "failed",
                                "error_stage": "api",
                                "error_code": type(e).__name__,
                                "reason": str(e)[:200],
                            })
                            self._log_combo_failure(
                                key, mdl, f"Exception {type(e).__name__}",
                                str(e),
                                provider=provider,
                            )
                            break  # try next combo
            if last_unparseable:
                content, mdl = last_unparseable
                parsed = _fallback_from_unparseable_response(content, mdl)
                parsed["provider_used"] = attempts[-1].get("provider", "")
                parsed["_api_attempts"] = attempts
                return parsed
            return None  # all combos exhausted
        finally:
            if close_session and self._session:
                await self._session.close()
                self._session = None

    async def verify_one(
        self, drug_a: str, drug_b: str, drug_b_ar: str = "",
        algo_score="", algo_method="", inventory_price=None,
        candidate_price=None,
    ) -> dict[str, Any]:
        """Verify a single match. Returns {is_correct, reason, confidence}."""
        if not self._cfg.api_key:
            return {"is_correct": True, "reason": "no_api_key", "confidence": 0.5}

        ar_line = f"\nDRUG B Arabic: {drug_b_ar}" if drug_b_ar else ""
        algorithm_context = (
            f"score={algo_score or '-'}, method={algo_method or '-'}"
        )
        prompt = render_prompt(
            VERIFY_PROMPT,
            drug_a=drug_a,
            drug_b=drug_b,
            drug_b_ar_line=ar_line,
            drug_a_context=_component_context(drug_a),
            drug_b_context=_component_context(drug_b),
            algorithm_context=algorithm_context,
            price_context=price_context(inventory_price, candidate_price),
        )
        payload = {
            "model": self._cfg.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._cfg.max_tokens,
            "temperature": self._cfg.temperature,
            "response_format": {"type": "json_object"},
        }

        result = await self._call_api(payload)
        if result is None:
            return {"is_correct": True, "reason": "all_api_failed", "confidence": 0.0, "api_failed": True}
        # Remove 'agree' key if present (not used in verify)
        result.pop("agree", None)
        return result

    async def verify_batch(self, matches: list[tuple]) -> list[dict[str, Any]]:
        """Verify a batch of matches. Each item is (drug_a, drug_b, drug_b_ar, row_index)."""
        normalized = [_normalize_verify_item(item) for item in matches]
        tasks = [
            self.verify_one(a, b, ar, score, method, inv_price, cand_price)
            for (
                a, b, ar, _, score, method, inv_price, cand_price
            ) in normalized
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        out = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                out.append({
                    "is_correct": True,
                    "reason": f"exception:{r}",
                    "confidence": 0.0,
                    "row_idx": normalized[i][3],
                })
            else:
                r["row_idx"] = normalized[i][3]
                out.append(r)
        return out

    async def review_one(
        self, drug_a: str, drug_b: str,
        first_decision: str, first_confidence: float, first_reason: str,
        api_failed: bool = False, drug_b_ar: str = "",
        inventory_price=None, candidate_price=None,
    ) -> dict[str, Any]:
        """Ask a second model to review the first AI's decision.
        If api_failed=True, the first AI never made a real decision — ask for fresh verification.
        Returns {is_correct, reason, confidence}."""
        review_model = self._cfg.review_model
        if not review_model or (not self._cfg.api_keys and not self._cfg.api_key):
            return {"is_correct": True, "reason": "no_review_model", "confidence": first_confidence}

        ar_line = f"\nDRUG B Arabic: {drug_b_ar}" if drug_b_ar else ""
        if api_failed:
            prompt = render_prompt(
                FRESH_REVIEW_PROMPT,
                drug_a=drug_a,
                drug_b=drug_b,
                drug_b_ar_line=ar_line,
                drug_a_context=_component_context(drug_a),
                drug_b_context=_component_context(drug_b),
                price_context=price_context(inventory_price, candidate_price),
            )
        else:
            decision_text = (
                "CORRECT match"
                if first_decision in {"ai_confirmed", "ai_corrected", "ai_found"}
                else "INCORRECT match"
            )
            prompt = render_prompt(
                REVIEW_PROMPT,
                drug_a=drug_a,
                drug_b=drug_b,
                drug_b_ar_line=ar_line,
                drug_a_context=_component_context(drug_a),
                drug_b_context=_component_context(drug_b),
                price_context=price_context(inventory_price, candidate_price),
                first_decision_text=decision_text,
                first_confidence=first_confidence,
                first_reason=first_reason,
            )

        payload = {
            "model": review_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._cfg.max_tokens,
            "temperature": self._cfg.temperature,
            "response_format": {"type": "json_object"},
        }

        result = await self._call_api(payload)
        if result is None:
            return {"is_correct": True, "reason": "review_all_api_failed", "confidence": first_confidence}

        if result.get("parse_failed"):
            return {
                "is_correct": not api_failed,
                "reason": str(result.get("reason", "invalid_json")),
                "confidence": min(float(result.get("confidence", 0.0)), 0.5),
                "parse_failed": True,
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
            }

        if api_failed:
            # Fresh verification: result is direct is_correct
            return {
                "is_correct": bool(result.get("is_correct", True)),
                "reason": str(result.get("reason", "")),
                "confidence": float(result.get("confidence", first_confidence)),
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
            }
        agree = bool(result.get("agree", True))
        # Resolve decision vs agree contradiction
        review_decision = str(result.get("decision", "")).lower().strip()
        if review_decision == "disagree" and agree:
            agree = False
        elif review_decision == "agree" and not agree:
            agree = True
        first_ai_said_correct = first_decision in {
            "ai_confirmed", "ai_corrected", "ai_found",
        }
        review_result = {
            "is_correct": agree if first_ai_said_correct else not agree,
            "reason": str(result.get("reason", "")),
            "confidence": float(result.get("confidence", first_confidence)),
            "model_used": result.get("model_used", ""),
            "provider_used": result.get("provider_used", ""),
            "hard_conflicts": result.get("hard_conflicts", []),
            "_api_attempts": result.get("_api_attempts", []),
        }
        # Apply hard_conflicts logic to review result as well
        return _resolve_ai_conflicts(review_result)

    async def review_batch(
        self, items: list[tuple]
    ) -> list[dict[str, Any]]:
        """Review a batch of first-AI decisions."""
        normalized = [_normalize_review_item(item) for item in items]
        tasks = [
            self.review_one(
                a, b, d, c, r, api_failed=f, drug_b_ar=ar,
                inventory_price=inv_price, candidate_price=cand_price,
            )
            for (
                a, b, ar, d, c, r, _, f, inv_price, cand_price
            ) in normalized
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                out.append({
                    "is_correct": True,
                    "reason": f"review_exception:{r}",
                    "confidence": normalized[i][4],
                    "row_idx": normalized[i][6],
                })
            else:
                r["row_idx"] = normalized[i][6]
                out.append(r)
        return out

    async def find_better_match(
        self, drug_name: str, candidates: list[tuple[dict, float, int]],
        inventory_price=None,
    ) -> dict[str, Any] | None:
        """Ask AI to pick the best match from candidates."""
        if not candidates or (not self._cfg.api_keys and not self._cfg.api_key):
            return None

        candidates_text = "\n".join(
            _format_candidate(i + 1, c, inventory_price)
            for i, c in enumerate(candidates[:5])
        )
        prompt = render_prompt(
            SEARCH_PROMPT,
            drug_name=drug_name,
            inventory_context=_component_context(drug_name),
            inventory_price=format_price(inventory_price),
            candidates_text=candidates_text,
            max_index=min(len(candidates), 5),
        )

        payload = {
            "model": self._cfg.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._cfg.max_tokens,
            "temperature": self._cfg.temperature,
            "response_format": {"type": "json_object"},
        }

        result = await self._call_api(payload)
        if result is None:
            return None
        raw = result.get("_raw", {})
        raw_best_index = raw.get("best_index", 0)
        max_index = min(len(candidates), 5)
        best_idx, valid_index = _coerce_best_index(raw_best_index, max_index)
        if not valid_index:
            return {
                "record": None, "score": 0.0,
                "reason": f"invalid_best_index:{str(raw_best_index)[:80]}",
                "confidence": min(float(result.get("confidence", 0.0)), 0.5),
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
                "best_index": 0,
                "parse_failed": True,
                "error_code": "invalid_best_index",
            }
        if best_idx > 0:
            return {
                "record": candidates[best_idx - 1][0],
                "score": candidates[best_idx - 1][1],
                "reason": result.get("reason", ""),
                "confidence": float(result.get("confidence", 0.0)),
                "model_used": result.get("model_used", ""),
                "provider_used": result.get("provider_used", ""),
                "_api_attempts": result.get("_api_attempts", []),
                "best_index": best_idx,
                "parse_failed": result.get("parse_failed", False),
            }
        return {
            "record": None, "score": 0.0,
            "reason": result.get("reason", "none"),
            "confidence": float(result.get("confidence", 0.0)),
            "model_used": result.get("model_used", ""),
            "provider_used": result.get("provider_used", ""),
            "_api_attempts": result.get("_api_attempts", []),
            "best_index": best_idx,
            "parse_failed": result.get("parse_failed", False),
        }
