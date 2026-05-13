"""Detailed algorithm trace logger - CSV + TXT output."""
import csv
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pharmasupplybot.matching")

_TRACE_CSV_COLS = [
    "run_id", "row_index", "phase", "decision", "decision_source",
    "error_stage", "error_code", "reject_rule",
    "inventory_components", "candidate_components",
    "base_score", "price_bonus", "final_candidate_score",
    "candidate_rank", "candidate_source",
    "threshold_name", "threshold_value",
    "api_attempt", "api_status", "model_used", "fallback_used",
    "parse_failed", "provider_used",
    "drug_code", "drug_name", "norm", "brand",
    "step", "candidate_name", "candidate_id",
    "candidate_brand", "candidate_norm",
    "score", "scorer", "threshold",
    "component_ok", "component_reason",
    "ai_phase", "ai_result", "ai_confidence",
    "ai_model", "ai_review_model", "api_failures",
    "selection_reason",
    "final_match", "final_score", "final_method",
]

_SUMMARY_COLS = [
    "code", "drug_name", "final_status", "final_match",
    "failure_stage", "primary_reason", "best_rejected_candidate",
    "ai_action", "ai_provider_model",
]


class MatchTraceLog:
    """Records every algorithmic + AI step for debugging."""

    __slots__ = ("_rows", "_dir", "_enabled", "_run_id")

    def __init__(self, log_dir: str | None = None, enabled: bool = True):
        self._enabled = enabled
        self._rows: list[dict] = []
        self._dir = Path(log_dir) if log_dir else Path("artifacts/matching/trace")
        self._run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if enabled:
            self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _base(self, code, name, norm, brand, **extra):
        row_index = extra.pop("row_index", "")
        return {
            "run_id": self._run_id, "row_index": row_index,
            "phase": "", "decision": "", "decision_source": "",
            "error_stage": "", "error_code": "", "reject_rule": "",
            "inventory_components": "", "candidate_components": "",
            "base_score": "", "price_bonus": "",
            "final_candidate_score": "", "candidate_rank": "",
            "candidate_source": "", "threshold_name": "",
            "threshold_value": "", "api_attempt": "",
            "api_status": "", "model_used": "", "fallback_used": "",
            "parse_failed": "", "provider_used": "",
            "drug_code": code, "drug_name": name,
            "norm": norm, "brand": brand,
            "step": "", "candidate_name": "",
            "candidate_id": "", "candidate_brand": "",
            "candidate_norm": "", "score": "",
            "scorer": "", "threshold": "",
            "component_ok": "", "component_reason": "",
            "ai_phase": "", "ai_result": "", "ai_confidence": "",
            "ai_model": "", "ai_review_model": "", "api_failures": "",
            "selection_reason": "",
            "final_match": "", "final_score": "",
            "final_method": "",
            **extra,
        }

    def _append(self, code, name, norm, brand, **extra):
        if not self._enabled:
            return
        self._rows.append(self._base(code, name, norm, brand, **extra))

    @staticmethod
    def components_text(comp) -> str:
        if not comp:
            return ""
        return (
            f"brand={comp.brand}; dosage={comp.dosage_nums or '-'}; "
            f"qty={comp.qty or '-'}; volume={comp.volume or '-'}; "
            f"weight={comp.weight or '-'}; form={comp.form or '-'}; "
            f"flavor={comp.flavor or '-'}; "
            f"imported={'yes' if comp.imported else 'no'}"
        )

    # --- Phase 1: algorithmic steps ---

    def log_normalization(
        self, code, name, norm, brand, dosage, form,
        row_index="", components="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="normalize",
            decision="parsed", decision_source="normalizer",
            inventory_components=components,
        )
        row["step"] = "normalize"
        row["selection_reason"] = f"dosage={dosage} form={form}"
        self._rows.append(row)

    def log_candidate_generated(
        self, code, name, norm, brand, candidate, index,
        source, rank="", score="", row_index="",
    ):
        if not self._enabled or candidate is None:
            return
        idx = candidate[0] if isinstance(candidate, tuple) else candidate
        rec = index.get_record(idx)
        parsed = index.get_parsed(idx)
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="candidate_generation",
            decision="generated", decision_source=source,
            candidate_source=source, candidate_rank=rank,
            candidate_components=self.components_text(parsed),
        )
        row["step"] = "candidate_generated"
        row["candidate_name"] = rec["product_name_en"]
        row["candidate_id"] = str(idx)
        row["candidate_brand"] = parsed.brand
        row["candidate_norm"] = parsed.normalized
        row["score"] = round(score, 1) if score not in (None, "") else ""
        row["selection_reason"] = f"{source} candidate rank={rank}"
        self._rows.append(row)

    def log_score_breakdown(
        self, code, name, norm, brand, item, index, row_index="",
    ):
        if not self._enabled:
            return
        idx = item["idx"]
        rec = index.get_record(idx)
        parsed = index.get_parsed(idx)
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="scoring",
            decision="score_calculated",
            decision_source=item.get("source", ""),
            candidate_source=item.get("source", ""),
            candidate_rank=item.get("rank", ""),
            base_score=round(item.get("base_score", 0), 1),
            price_bonus=round(item.get("price_bonus", 0), 1),
            final_candidate_score=round(item.get("final_score", 0), 1),
            threshold_name="fuzzy_threshold",
            threshold_value=item.get("threshold", ""),
            candidate_components=self.components_text(parsed),
        )
        row["step"] = "score_breakdown"
        row["candidate_name"] = rec["product_name_en"]
        row["candidate_id"] = str(idx)
        row["candidate_brand"] = parsed.brand
        row["candidate_norm"] = parsed.normalized
        row["score"] = round(item.get("final_score", 0), 1)
        row["selection_reason"] = (
            f"base={row['base_score']} + price_bonus={row['price_bonus']} "
            f"=> final={row['final_candidate_score']}"
        )
        self._rows.append(row)

    def log_brand_lookup(
        self, code, name, norm, brand, hits, index, row_index="",
    ):
        if not self._enabled:
            return
        if not hits:
            row = self._base(
                code, name, norm, brand,
                row_index=row_index, phase="candidate_generation",
                decision="no_candidates", decision_source="brand_index",
                error_stage="candidate_generation", error_code="no_brand_hits",
            )
            row["step"] = "brand_lookup"
            row["selection_reason"] = (
                f"brand={brand} len={len(brand)} (need >=3)"
            )
            row["ai_result"] = "no_hits"
            self._rows.append(row)
            return
        for rank, (idx, score) in enumerate(hits, start=1):
            rec = index.get_record(idx)
            parsed = index.get_parsed(idx)
            row = self._base(
                code, name, norm, brand,
                row_index=row_index, phase="candidate_generation",
                decision="generated", decision_source="brand_index",
                candidate_source="brand_index", candidate_rank=rank,
                candidate_components=self.components_text(parsed),
            )
            row["step"] = "brand_lookup"
            row["candidate_name"] = rec["product_name_en"]
            row["candidate_id"] = str(idx)
            row["candidate_brand"] = parsed.brand
            row["candidate_norm"] = parsed.normalized
            row["score"] = round(score, 1)
            row["scorer"] = "token_sort_ratio"
            row["selection_reason"] = (
                f"brand_prefix_match score={round(score, 1)}"
            )
            self._rows.append(row)

    def log_fuzzy_step(
        self, code, name, norm, brand,
        scorer_name, result, threshold, index,
        row_index="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="candidate_generation",
            decision_source=f"fuzzy:{scorer_name}",
            threshold_name="fuzzy_threshold",
            threshold_value=threshold,
        )
        row["step"] = "fuzzy"
        row["scorer"] = scorer_name
        row["threshold"] = threshold
        if result:
            match_name, score, idx = result
            rec = index.get_record(idx)
            parsed = index.get_parsed(idx)
            row["candidate_name"] = match_name
            row["candidate_id"] = str(idx)
            row["candidate_brand"] = parsed.brand
            row["candidate_norm"] = parsed.normalized
            row["candidate_components"] = self.components_text(parsed)
            row["candidate_source"] = f"fuzzy:{scorer_name}"
            row["decision"] = "generated"
            row["score"] = round(score, 1)
            row["selection_reason"] = (
                f"score={round(score, 1)} >= threshold={threshold}"
            )
        else:
            row["decision"] = "no_candidates"
            row["error_stage"] = "candidate_generation"
            row["error_code"] = "below_threshold"
            row["selection_reason"] = (
                f"no candidate above threshold={threshold}"
            )
        self._rows.append(row)

    def log_component_check(
        self, code, name, norm, brand,
        cidx, ok, reason, index,
        row_index="",
    ):
        if not self._enabled:
            return
        rec = index.get_record(cidx)
        parsed = index.get_parsed(cidx)
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="component_check",
            decision="accepted" if ok else "rejected",
            decision_source="components_match",
            reject_rule="" if ok else reason,
            error_stage="" if ok else "component_check",
            error_code="" if ok else reason,
            candidate_components=self.components_text(parsed),
        )
        row["step"] = "component_check"
        row["candidate_name"] = rec["product_name_en"]
        row["candidate_id"] = str(cidx)
        row["candidate_brand"] = parsed.brand
        row["candidate_norm"] = parsed.normalized
        row["component_ok"] = "yes" if ok else "no"
        row["component_reason"] = reason
        row["selection_reason"] = (
            f"components_match={'ok' if ok else 'FAIL'}"
            f" reason={reason}"
        )
        self._rows.append(row)

    def log_final(
        self, code, name, norm, brand,
        match, score, method, ai_eligible, ai_reason,
        row_index="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="final",
            decision="matched" if match else "no_match",
            decision_source=method,
            error_stage="" if match else "matching",
            error_code="" if match else method,
            threshold_name="ai_verify_threshold",
        )
        row["step"] = "final"
        row["final_match"] = match or "NONE"
        row["final_score"] = round(score, 1) if score else ""
        row["final_method"] = method
        row["ai_phase"] = (
            "verify" if ai_eligible == "verify"
            else "search" if ai_eligible == "search"
            else "none"
        )
        row["ai_result"] = ai_eligible
        row["selection_reason"] = ai_reason
        self._rows.append(row)

    # --- Phase 2 & 3: AI steps ---

    def log_ai_verify_sent(
        self, code, name, norm, brand, score, threshold,
        matched_name, matched_brand, method,
        ai_model="", price_context="", row_index="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_verify",
            decision="sent", decision_source="ai_verify",
            threshold_name="ai_verify_threshold",
            threshold_value=threshold,
        )
        row["step"] = "ai_verify_sent"
        row["ai_phase"] = "verify"
        row["score"] = round(score, 1)
        row["threshold"] = threshold
        row["candidate_name"] = matched_name or ""
        row["candidate_brand"] = matched_brand or ""
        row["scorer"] = method
        row["ai_model"] = ai_model
        row["selection_reason"] = (
            f"algo matched '{matched_name}' "
            f"(brand={matched_brand}) "
            f"score={round(score, 1)} < ai_threshold={threshold}"
            f" -> sent to AI model={ai_model} to verify correctness"
        )
        if price_context:
            row["selection_reason"] += f" | price_context={price_context}"
        self._rows.append(row)

    def log_ai_verify_result(
        self, code, name, norm, brand,
        is_correct, ai_action, detail,
        matched_name, confidence, ai_reason,
        corrected_to,
        model_used="", api_failures="", row_index="",
        parse_failed=False,
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_verify",
            decision=ai_action, decision_source="ai_verify",
            error_stage="" if is_correct else "ai_verify",
            error_code="" if is_correct else ai_action,
            model_used=model_used, parse_failed=str(bool(parse_failed)).lower(),
        )
        row["step"] = "ai_verify_result"
        row["ai_phase"] = "verify"
        row["ai_result"] = ai_action
        row["ai_confidence"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["candidate_name"] = matched_name or ""
        row["score"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["ai_model"] = model_used
        row["api_failures"] = api_failures
        row["selection_reason"] = (
            f"AI_says={'correct' if is_correct else 'incorrect'}"
            f" model={model_used}"
            f" confidence={round(float(confidence), 2) if confidence not in (None, '') else 'N/A'}"
            f" reason='{ai_reason}'"
            f" action={ai_action}"
        )
        if api_failures:
            row["selection_reason"] += f" | API_failures: {api_failures}"
        if corrected_to:
            row["component_reason"] = f"corrected_to={corrected_to}"
        self._rows.append(row)

    def log_ai_search_sent(
        self, code, name, norm, brand,
        n_candidates, candidate_names,
        ai_model="", price_context="", row_index="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_search",
            decision="sent", decision_source="ai_search",
            candidate_source="ai_candidates",
        )
        row["step"] = "ai_search_sent"
        row["ai_phase"] = "search"
        row["candidate_name"] = "; ".join(candidate_names[:5])
        row["ai_model"] = ai_model
        row["selection_reason"] = (
            f"no_match + {n_candidates} candidates found"
            f" -> sent to AI model={ai_model} to pick best match"
        )
        if price_context:
            row["selection_reason"] += f" | price_context={price_context}"
        self._rows.append(row)

    def log_ai_search_result(
        self, code, name, norm, brand,
        found, match_name, confidence,
        model_used="", api_failures="", accept_threshold=0.75,
        row_index="", error_code="", parse_failed=False,
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_search",
            decision="ai_found" if found else "not_found",
            decision_source="ai_search",
            error_stage="" if found else "ai_search",
            error_code=error_code if not found else "",
            threshold_name="ai_search_accept_confidence",
            threshold_value=accept_threshold,
            model_used=model_used,
            parse_failed=str(bool(parse_failed)).lower(),
        )
        row["step"] = "ai_search_result"
        row["ai_phase"] = "search"
        row["ai_result"] = "ai_found" if found else "not_found"
        row["ai_confidence"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["candidate_name"] = match_name or ""
        row["score"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["ai_model"] = model_used
        row["api_failures"] = api_failures
        confidence_text = (
            round(float(confidence), 2)
            if confidence not in (None, "") else "N/A"
        )
        if found:
            threshold_text = f" >= {accept_threshold} -> accepted"
        elif confidence not in (None, "") and float(confidence) < float(accept_threshold):
            threshold_text = f" < {accept_threshold} -> rejected"
        elif error_code:
            threshold_text = f" error={error_code} -> rejected"
        else:
            threshold_text = f" >= {accept_threshold} but no accepted record -> rejected"
        row["selection_reason"] = (
            f"AI_model={model_used}"
            f" confidence={confidence_text}"
            f"{threshold_text}"
        )
        if api_failures:
            row["selection_reason"] += f" | API_failures: {api_failures}"
        self._rows.append(row)

    def log_ai_review_sent(
        self, code, name, norm, brand,
        first_decision, first_confidence, matched_name,
        first_model="", review_model="", api_failed=False,
        price_context="", row_index="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_review",
            decision="sent", decision_source="ai_review",
            model_used=first_model,
        )
        row["step"] = "ai_review_sent"
        row["ai_phase"] = "review"
        row["ai_result"] = first_decision
        row["ai_confidence"] = round(float(first_confidence), 2) if first_confidence not in (None, "") else ""
        row["candidate_name"] = matched_name or ""
        row["ai_model"] = first_model
        row["ai_review_model"] = review_model
        if api_failed:
            row["selection_reason"] = (
                f"first_AI=UNAVAILABLE (API failed)"
                f" -> sent to review model={review_model} for FRESH verification"
            )
        else:
            row["selection_reason"] = (
                f"first_AI={first_decision} model={first_model}"
                f" confidence={round(float(first_confidence), 2) if first_confidence not in (None, '') else 'N/A'}"
                f" < review_threshold -> sent to review model={review_model}"
            )
        if price_context:
            row["selection_reason"] += f" | price_context={price_context}"
        self._rows.append(row)

    def log_ai_review_result(
        self, code, name, norm, brand,
        agree, review_confidence, review_reason, final_action,
        review_model="", api_failures="", row_index="",
        parse_failed=False,
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_review",
            decision=final_action, decision_source="ai_review",
            error_stage="" if agree else "ai_review",
            error_code="" if agree else final_action,
            model_used=review_model,
            parse_failed=str(bool(parse_failed)).lower(),
        )
        row["step"] = "ai_review_result"
        row["ai_phase"] = "review"
        row["ai_result"] = final_action
        row["ai_confidence"] = round(float(review_confidence), 2) if review_confidence not in (None, "") else ""
        row["ai_review_model"] = review_model
        row["api_failures"] = api_failures
        row["selection_reason"] = (
            f"second_AI={'agrees' if agree else 'disagrees'}"
            f" model={review_model}"
            f" confidence={round(float(review_confidence), 2) if review_confidence not in (None, '') else 'N/A'}"
            f" reason='{review_reason}'"
            f" action={final_action}"
        )
        if api_failures:
            row["selection_reason"] += f" | API_failures: {api_failures}"
        self._rows.append(row)

    def log_ai_skip(self, code, name, norm, brand, phase, reason, row_index=""):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase=f"ai_{phase}",
            decision="skipped", decision_source=f"ai_{phase}",
            error_stage=f"ai_{phase}", error_code=reason,
        )
        row["step"] = "ai_skip"
        row["ai_phase"] = phase
        row["ai_result"] = "skipped"
        row["selection_reason"] = reason
        self._rows.append(row)

    def log_ai_search_not_eligible(
        self, code, name, norm, brand, reason, row_index="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_search",
            decision="skipped", decision_source="ai_search",
            error_stage="ai_search", error_code="not_eligible",
        )
        row["step"] = "ai_search_not_eligible"
        row["ai_phase"] = "search"
        row["ai_result"] = "skipped"
        row["selection_reason"] = reason
        self._rows.append(row)

    def log_ai_preflight_start(self, models, key_count):
        self._append(
            "", "", "", "",
            step="ai_preflight_start",
            phase="ai_preflight",
            decision="started",
            decision_source="ai_health",
            selection_reason=(
                f"testing {key_count} key(s) x {len(models)} model(s): "
                f"{', '.join(models)}"
            ),
        )

    def log_ai_preflight_result(self, rows, healthy_count):
        status = "healthy" if healthy_count else "no_healthy_model"
        self._append(
            "", "", "", "",
            step="ai_preflight_result",
            phase="ai_preflight",
            decision=status,
            decision_source="ai_health",
            error_stage="" if healthy_count else "ai_preflight",
            error_code="" if healthy_count else "no_healthy_model",
            selection_reason=(
                f"healthy_combos={healthy_count}; "
                f"tested={len(rows)}; "
                f"failures={self._preflight_failures(rows)}"
            ),
        )

    @staticmethod
    def _preflight_failures(rows):
        counts = {}
        for row in rows:
            if row.get("ok"):
                continue
            key = row.get("error_type") or "unknown"
            counts[key] = counts.get(key, 0) + 1
        return "; ".join(f"{k}:{v}" for k, v in sorted(counts.items()))

    def log_rotation_preflight_start(self, attempts_count, detail=""):
        reason = f"testing {attempts_count} provider/key/model attempts"
        if detail:
            reason = f"{reason}; {detail}"
        self._append(
            "", "", "", "",
            step="rotation_preflight_start",
            phase="ai_rotation",
            decision="started",
            decision_source="ai_rotation",
            selection_reason=reason,
        )

    def log_rotation_ranked_attempt(self, row):
        self._append(
            "", "", "", "",
            step="rotation_ranked_attempt",
            phase="ai_rotation",
            decision="healthy" if row.get("ok") else "failed",
            decision_source="ai_rotation",
            provider_used=row.get("provider", ""),
            model_used=row.get("model", ""),
            candidate_rank=row.get("rotation_rank", ""),
            api_status=row.get("http_status", ""),
            error_stage="" if row.get("ok") else "ai_rotation",
            error_code="" if row.get("ok") else row.get("error_type", ""),
            selection_reason=(
                f"rank={row.get('rotation_rank')} "
                f"provider={row.get('provider')} "
                f"model={row.get('model')} "
                f"key=...{row.get('key_suffix', '')} "
                f"score={row.get('rotation_score')} "
                f"reset={row.get('quota_reset_in') or row.get('retry_after_in') or 'n/a'}"
            ),
        )

    def log_api_attempts(self, code, name, norm, brand, attempts, row_index=""):
        if not self._enabled:
            return
        for item in attempts or []:
            row = self._base(
                code, name, norm, brand,
                row_index=row_index, phase="api",
                decision=item.get("decision", ""),
                decision_source="api_client",
                error_stage=item.get("error_stage", ""),
                error_code=item.get("error_code", ""),
                api_attempt=item.get("attempt", ""),
                api_status=item.get("status", ""),
                model_used=item.get("model", ""),
                provider_used=item.get("provider", ""),
                fallback_used=str(bool(item.get("fallback_used"))).lower(),
                parse_failed=str(bool(item.get("parse_failed"))).lower(),
            )
            row["step"] = "api_attempt"
            row["ai_phase"] = item.get("phase", "")
            row["ai_model"] = item.get("model", "")
            suffix = item.get("key_suffix", "")
            key_txt = f" key=...{suffix}" if suffix else ""
            row["selection_reason"] = f"{item.get('reason', '')}{key_txt}"
            self._rows.append(row)
            self._append_rotation_attempt_event(code, name, norm, brand, item, row_index)

    def _append_rotation_attempt_event(
        self, code, name, norm, brand, item, row_index="",
    ):
        provider = item.get("provider", "")
        if not provider:
            return
        decision = item.get("decision", "")
        if decision == "success":
            step = "rotation_attempt_used"
        elif decision == "disabled":
            step = "rotation_attempt_disabled"
        else:
            return
        self._append(
            code, name, norm, brand,
            row_index=row_index, phase="ai_rotation",
            step=step, decision=decision,
            decision_source="ai_rotation",
            provider_used=provider,
            model_used=item.get("model", ""),
            api_status=item.get("status", ""),
            error_stage=item.get("error_stage", ""),
            error_code=item.get("error_code", ""),
            selection_reason=(
                f"{step}: provider={provider} "
                f"model={item.get('model', '')} "
                f"key=...{item.get('key_suffix', '')} "
                f"reason={item.get('reason', '')}"
            ),
        )

    def log_ai_parse_failure(
        self, code, name, norm, brand, raw_excerpt,
        model_used="", row_index="",
    ):
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_parse",
            decision="parse_failed", decision_source="ai_client",
            error_stage="ai_parse", error_code="invalid_json",
            model_used=model_used, parse_failed="true",
        )
        row["step"] = "ai_parse_failure"
        row["ai_model"] = model_used
        row["selection_reason"] = raw_excerpt[:200]
        self._rows.append(row)

    # --- output ---

    def save(self, prefix: str = "trace") -> tuple[str, str, str]:
        if not self._enabled or not self._rows:
            return "", "", ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self._dir / f"{prefix}_{ts}.csv"
        txt_path = self._dir / f"{prefix}_{ts}.txt"
        summary_path = self._dir / f"{prefix}_summary_{ts}.csv"
        self._save_csv(csv_path)
        self._save_txt(txt_path)
        self.save_summary(summary_path)
        logger.info(
            f"Trace saved: {csv_path} + {txt_path} + {summary_path}",
        )
        return str(csv_path), str(txt_path), str(summary_path)

    def _save_csv(self, path: Path):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_TRACE_CSV_COLS)
            writer.writeheader()
            writer.writerows(self._rows)

    def save_summary(self, path: Path):
        rows = self._summary_rows()
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_SUMMARY_COLS)
            writer.writeheader()
            writer.writerows(rows)

    def _summary_rows(self):
        grouped: dict[tuple[str, str], list[dict]] = {}
        for row in self._rows:
            if not row["drug_code"] and not row["drug_name"]:
                continue
            grouped.setdefault(
                (row["drug_code"], row["drug_name"]), [],
            ).append(row)
        return [self._summary_row(code, name, rows)
                for (code, name), rows in grouped.items()]

    def _summary_row(self, code, name, rows):
        final = self._last(rows, "final")
        last_ai = self._last_ai_result(rows)
        ai_rows = [r for r in rows if r.get("ai_result")]
        rejected = [
            r for r in rows
            if r.get("decision") == "rejected" or r.get("reject_rule")
        ]
        if last_ai and self._ai_summary_status(last_ai) == "rejected":
            status = "no_match"
            final_match = "NONE"
        elif last_ai and self._ai_summary_status(last_ai) == "matched":
            status = "matched"
            final_match = last_ai.get("candidate_name", "") or self._last_candidate_name(rows)
        elif final:
            status = "matched" if final.get("final_match") != "NONE" else "no_match"
            final_match = final.get("final_match", "")
        else:
            status = "unknown"
            final_match = ""
        primary = (rejected[-1] if rejected else final) or rows[-1]
        failure_stage = primary.get("error_stage")
        if not failure_stage and status == "no_match":
            failure_stage = "matching"
        reason = (
            primary.get("error_code") or primary.get("reject_rule")
            or primary.get("selection_reason") or ""
        )
        best_rejected = rejected[-1].get("candidate_name", "") if rejected else ""
        return {
            "code": code,
            "drug_name": name,
            "final_status": status,
            "final_match": final_match,
            "failure_stage": failure_stage,
            "primary_reason": reason,
            "best_rejected_candidate": best_rejected,
            "ai_action": ai_rows[-1].get("ai_result", "") if ai_rows else "",
            "ai_provider_model": self._provider_model(rows),
        }

    @staticmethod
    def _last(rows, step):
        for row in reversed(rows):
            if row.get("step") == step:
                return row
        return None

    @staticmethod
    def _last_ai_result(rows):
        for row in reversed(rows):
            if row.get("step") in {
                "ai_verify_result", "ai_search_result", "ai_review_result",
            }:
                return row
        return None

    @staticmethod
    def _ai_summary_status(row):
        result = row.get("ai_result", "")
        if result in {"ai_rejected", "ai_review_rejected", "not_found"}:
            return "rejected"
        if result in {
            "ai_found", "ai_corrected", "ai_review_corrected",
            "ai_confirmed",
        }:
            return "matched"
        if result.endswith("_reviewed"):
            base = result.removesuffix("_reviewed")
            if base in {"ai_found", "ai_corrected", "ai_confirmed"}:
                return "matched"
        if result.endswith("_kept_low_confidence_review"):
            base = result.removesuffix("_kept_low_confidence_review")
            if base in {"ai_found", "ai_corrected", "ai_confirmed"}:
                return "matched"
            if base == "ai_rejected":
                return "rejected"
        return ""

    @staticmethod
    def _last_candidate_name(rows):
        for row in reversed(rows):
            candidate = row.get("candidate_name")
            if candidate:
                return candidate
            final_match = row.get("final_match")
            if final_match and final_match != "NONE":
                return final_match
        return ""

    @staticmethod
    def _provider_model(rows):
        for row in reversed(rows):
            provider = row.get("provider_used")
            model = row.get("model_used") or row.get("ai_model")
            if provider or model:
                return f"{provider}/{model}".strip("/")
        return ""

    def _save_txt(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("MediCompare Algorithm Trace Log\n")
            f.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"Total steps: {len(self._rows)}\n")
            f.write("=" * 80 + "\n\n")
            current_drug = None
            for row in self._rows:
                key = (row["drug_code"], row["drug_name"])
                if key != current_drug:
                    current_drug = key
                    f.write("-" * 60 + "\n")
                    f.write(
                        f"DRUG: [{row['drug_code']}] "
                        f"{row['drug_name']}\n",
                    )
                    f.write(
                        f"  norm={row['norm']}  "
                        f"brand={row['brand']}\n",
                    )
                self._write_step(f, row)
            f.write("=" * 80 + "\n")

    def _write_step(self, f, row):
        step = row["step"]
        if step == "normalize":
            f.write(f"  [normalize] {row['selection_reason']}\n")
        elif step == "brand_lookup":
            if row["ai_result"] == "no_hits":
                f.write(
                    f"  [brand_lookup] no hits  "
                    f"({row['selection_reason']})\n",
                )
            else:
                f.write(
                    f"  [brand_lookup] "
                    f"{row['candidate_name']}"
                    f"  brand={row['candidate_brand']}"
                    f"  score={row['score']}\n",
                )
        elif step == "fuzzy":
            if "no candidate" in row.get("selection_reason", ""):
                f.write(
                    f"  [fuzzy/{row['scorer']}] "
                    f"no hit above threshold={row['threshold']}\n",
                )
            else:
                f.write(
                    f"  [fuzzy/{row['scorer']}] "
                    f"{row['candidate_name']}"
                    f"  brand={row['candidate_brand']}"
                    f"  score={row['score']}"
                    f"  (threshold={row['threshold']})\n",
                )
        elif step == "component_check":
            f.write(
                f"  [component_check] "
                f"{row['candidate_name']}"
                f"  brand={row['candidate_brand']}"
                f"  ok={row['component_ok']}"
                f"  reason={row['component_reason']}"
                f"  reject_rule={row.get('reject_rule', '')}\n",
            )
        elif step == "candidate_generated":
            f.write(
                f"  [candidate/{row['candidate_source']}] "
                f"rank={row['candidate_rank']} "
                f"{row['candidate_name']} score={row['score']}\n",
            )
        elif step == "score_breakdown":
            f.write(
                f"  [score/{row['candidate_source']}] "
                f"{row['candidate_name']} base={row['base_score']} "
                f"price_bonus={row['price_bonus']} "
                f"final={row['final_candidate_score']}\n",
            )
        elif step == "final":
            ai = row["ai_phase"]
            ai_txt = f"  AI={ai}" if ai != "none" else ""
            f.write(
                f"  >> FINAL: match={row['final_match']}"
                f"  score={row['final_score']}"
                f"  method={row['final_method']}"
                f"{ai_txt}\n",
            )
            f.write(f"     reason: {row['selection_reason']}\n\n")
        elif step == "ai_verify_sent":
            model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
            f.write(
                f"  [AI VERIFY] sent to verify: "
                f"'{row['candidate_name']}'"
                f"  (brand={row['candidate_brand']})"
                f"  score={row['score']} < threshold={row['threshold']}"
                f"{model_txt}\n",
            )
        elif step == "ai_verify_result":
            model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
            api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
            f.write(
                f"  [AI VERIFY] result={row['ai_result']}  "
                f"verifying='{row['candidate_name']}'  "
                f"confidence={row['score']}"
                f"{model_txt}{api_txt}\n",
            )
            f.write(
                f"     {row['selection_reason']}\n",
            )
            if row.get('component_reason'):
                f.write(
                    f"     {row['component_reason']}\n",
                )
        elif step == "ai_search_sent":
            model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
            f.write(
                f"  [AI SEARCH] sent with {row['selection_reason']}{model_txt}\n"
            )
            if row.get('candidate_name'):
                f.write(
                    f"     candidates: {row['candidate_name']}\n"
                )
        elif step == "ai_search_result":
            model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
            api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
            if row["ai_result"] == "ai_found":
                f.write(
                    f"  [AI SEARCH] FOUND: "
                    f"{row['candidate_name']}"
                    f"  confidence={row['score']}"
                    f"{model_txt}{api_txt}\n",
                )
            else:
                f.write(
                    f"  [AI SEARCH] not found  "
                    f"{row['selection_reason']}{api_txt}\n",
                )
        elif step == "ai_review_sent":
            first_model_txt = f"  first_model={row['ai_model']}" if row.get('ai_model') else ""
            review_model_txt = f"  review_model={row['ai_review_model']}" if row.get('ai_review_model') else ""
            f.write(
                f"  [AI REVIEW] sent to second model: "
                f"first_decision={row['ai_result']}  "
                f"first_confidence={row['ai_confidence']}"
                f"{first_model_txt}{review_model_txt}\n",
            )
            f.write(
                f"     {row['selection_reason']}\n",
            )
        elif step == "ai_review_result":
            review_model_txt = f"  review_model={row['ai_review_model']}" if row.get('ai_review_model') else ""
            api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
            f.write(
                f"  [AI REVIEW] result={row['ai_result']}  "
                f"review_confidence={row['ai_confidence']}"
                f"{review_model_txt}{api_txt}\n",
            )
            f.write(
                f"     {row['selection_reason']}\n",
            )
        elif step == "ai_skip":
            f.write(
                f"  [AI {row['ai_phase'].upper()}] "
                f"SKIPPED: {row['selection_reason']}\n",
            )
        elif step == "ai_search_not_eligible":
            f.write(
                f"  [AI SEARCH] NOT ELIGIBLE: "
                f"{row['selection_reason']}\n",
            )
        elif step in {"rotation_preflight_start", "rotation_ranked_attempt"}:
            f.write(f"  [AI ROTATION] {row['selection_reason']}\n")
        elif step in {"rotation_attempt_used", "rotation_attempt_disabled"}:
            f.write(f"  [AI ROTATION] {row['selection_reason']}\n")
        elif step in {"ai_preflight_start", "ai_preflight_result"}:
            f.write(f"  [AI PREFLIGHT] {row['selection_reason']}\n")
        elif step == "api_attempt":
            f.write(
                f"  [API] model={row['model_used']} "
                f"status={row['api_status']} "
                f"fallback={row['fallback_used']} "
                f"parse_failed={row['parse_failed']} "
                f"{row['selection_reason']}\n",
            )
        elif step == "ai_parse_failure":
            f.write(
                f"  [AI PARSE] model={row['model_used']} "
                f"invalid_json excerpt={row['selection_reason']}\n",
            )
