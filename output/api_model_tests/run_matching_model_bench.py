"""Run SMALL_TEST match-only for baseline + each config AI model, then rank."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "api_model_tests"
OUT.mkdir(parents=True, exist_ok=True)
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")
EXCEL = "data/input/order_items/SMALL_TEST.xlsx"
CONFIG = "state/config.yaml"
PROFILE = "wardany"
ARTIFACTS = ROOT / "artifacts" / "order" / PROFILE

# Models from config + known healthy best. provider pin is critical for correct base_url.
MODELS = [
    {"label": "baseline_no_ai", "ai": False, "provider": None, "model": None},
    {"label": "opencode/big-pickle", "ai": True, "provider": "opencode", "model": "big-pickle"},
    {"label": "mistral/mistral-large-latest", "ai": True, "provider": "mistral", "model": "mistral-large-latest"},
    {"label": "mistral/mistral-medium-latest", "ai": True, "provider": "mistral", "model": "mistral-medium-latest"},
    {"label": "openrouter/openai-gpt-4o", "ai": True, "provider": "openrouter", "model": "openai/gpt-4o"},
    {
        "label": "openrouter/llama-3.3-70b",
        "ai": True,
        "provider": "openrouter",
        "model": "meta-llama/llama-3.3-70b-instruct",
    },
    {"label": "google/gemini-2.5-flash", "ai": True, "provider": "google", "model": "models/gemini-2.5-flash"},
]


def newest_summary_after(before: float) -> Path | None:
    cands = []
    for p in ARTIFACTS.glob("*/order_item_summary_*.csv"):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if mtime >= before - 1:
            cands.append((mtime, p))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0][1]


def run_one(spec: dict) -> dict:
    label = spec["label"]
    log_path = OUT / f"run_{label.replace('/', '_')}.log"
    cmd = [
        PYTHON,
        "run.py",
        "order",
        "--config",
        CONFIG,
        "--profile",
        PROFILE,
        "--excel",
        EXCEL,
        "--execution-mode",
        "api",
        "--match-only",
        "--limit=30",
        "--no-ai-preflight",
    ]
    if spec["ai"]:
        cmd += ["--ai", "--provider", spec["provider"], "--model", spec["model"]]
        # keep review on same model to avoid cross-provider noise
        cmd += ["--review-model", spec["model"]]

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONUNBUFFERED"] = "1"

    print(f"\n=== RUN {label} ===", flush=True)
    print("CMD:", " ".join(cmd), flush=True)
    t0 = time.time()
    before = time.time()
    with log_path.open("w", encoding="utf-8", errors="replace") as logf:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
        )
    elapsed = time.time() - t0
    summary = newest_summary_after(before)
    result = {
        "label": label,
        "ai": spec["ai"],
        "provider": spec.get("provider"),
        "model": spec.get("model"),
        "exit_code": proc.returncode,
        "elapsed_s": round(elapsed, 2),
        "log": str(log_path.relative_to(ROOT)),
        "summary_csv": str(summary.relative_to(ROOT)) if summary else None,
        "artifact_dir": str(summary.parent.relative_to(ROOT)) if summary else None,
    }
    print(
        f"DONE {label} exit={proc.returncode} elapsed={elapsed:.1f}s summary={summary}",
        flush=True,
    )
    return result


def score_summary(csv_path: Path | None, baseline_map: dict | None = None) -> dict:
    if not csv_path or not csv_path.exists():
        return {"error": "no_summary", "n_items": 0}
    df = pd.read_csv(csv_path)
    n = len(df)
    status = df["status"].fillna("").astype(str)
    matched_only = int((status == "matched-only").sum())
    not_orderable = int((status == "not-orderable").sum())
    no_results = int((status == "no-results").sum())
    other = n - matched_only - not_orderable - no_results
    matched_flag = (
        df["matched"].fillna(False).astype(bool).sum() if "matched" in df.columns else 0
    )
    name_nonempty = (
        df["matched_product_name_en"].fillna("").astype(str).str.strip().ne("").sum()
        if "matched_product_name_en" in df.columns
        else 0
    )
    ai_enabled = (
        int(df["ai_enabled"].fillna(False).astype(bool).sum())
        if "ai_enabled" in df.columns
        else 0
    )
    ai_status = (
        df["ai_status"].fillna("").astype(str).value_counts().to_dict()
        if "ai_status" in df.columns
        else {}
    )
    ai_verified = (
        int(df["ai_verified"].fillna(False).astype(bool).sum())
        if "ai_verified" in df.columns
        else 0
    )
    ai_searched = (
        int(df["ai_searched"].fillna(False).astype(bool).sum())
        if "ai_searched" in df.columns
        else 0
    )
    ai_reviewed = (
        int(df["ai_reviewed"].fillna(False).astype(bool).sum())
        if "ai_reviewed" in df.columns
        else 0
    )
    conf = (
        pd.to_numeric(df.get("ai_confidence"), errors="coerce")
        if "ai_confidence" in df.columns
        else pd.Series(dtype=float)
    )
    conf_non_null = conf.dropna()
    models_used = (
        df["ai_model"].dropna().astype(str).value_counts().to_dict()
        if "ai_model" in df.columns
        else {}
    )
    providers_used = (
        df["ai_provider"].dropna().astype(str).value_counts().to_dict()
        if "ai_provider" in df.columns
        else {}
    )
    manual_review = (
        int(df["manual_review_required"].fillna(False).astype(bool).sum())
        if "manual_review_required" in df.columns
        else 0
    )

    # agreement with baseline product ids / names
    agree_id = agree_name = disagree = missing_base = 0
    if baseline_map is not None and "item_code" in df.columns:
        for _, row in df.iterrows():
            code = str(row.get("item_code") if pd.notna(row.get("item_code")) else "").strip()
            name = str(row.get("item_name") or "").strip()
            key = code or name
            base = baseline_map.get(key)
            if not base:
                missing_base += 1
                continue
            cur_id = str(row.get("matched_product_id") or "").strip()
            base_id = str(base.get("matched_product_id") or "").strip()
            cur_name = str(row.get("matched_product_name_en") or "").strip().upper()
            base_name = str(base.get("matched_product_name_en") or "").strip().upper()
            if cur_id and base_id and cur_id == base_id:
                agree_id += 1
            elif cur_name and base_name and cur_name == base_name:
                agree_name += 1
            else:
                disagree += 1

    # quality score (0-100): prioritize orderable matches + AI evidence + name fill + agreement
    orderable_rate = matched_only / n if n else 0
    name_rate = name_nonempty / n if n else 0
    ai_evidence = (ai_verified + ai_searched) / n if n and ai_enabled else 0
    conf_mean = float(conf_non_null.mean()) if len(conf_non_null) else 0.0
    agree_rate = (agree_id + agree_name) / max(1, agree_id + agree_name + disagree) if baseline_map else orderable_rate
    # weighted
    if ai_enabled:
        quality = (
            40 * orderable_rate
            + 20 * name_rate
            + 15 * agree_rate
            + 15 * min(1.0, ai_evidence)
            + 10 * min(1.0, conf_mean)
        )
    else:
        quality = 50 * orderable_rate + 30 * name_rate + 20 * agree_rate

    return {
        "n_items": n,
        "matched_only": matched_only,
        "not_orderable": not_orderable,
        "no_results": no_results,
        "other_status": other,
        "matched_flag": int(matched_flag),
        "name_nonempty": int(name_nonempty),
        "orderable_rate": round(orderable_rate, 4),
        "name_rate": round(name_rate, 4),
        "ai_enabled_rows": ai_enabled,
        "ai_status": ai_status,
        "ai_verified": ai_verified,
        "ai_searched": ai_searched,
        "ai_reviewed": ai_reviewed,
        "ai_conf_mean": round(float(conf_non_null.mean()), 4) if len(conf_non_null) else None,
        "ai_conf_non_null": int(len(conf_non_null)),
        "manual_review_required": manual_review,
        "models_used": models_used,
        "providers_used": providers_used,
        "agree_product_id": agree_id,
        "agree_product_name": agree_name,
        "disagree_vs_baseline": disagree,
        "missing_baseline_key": missing_base,
        "quality_score": round(quality, 2),
        "rows_preview": df[
            [
                c
                for c in [
                    "item_code",
                    "item_name",
                    "status",
                    "matched_product_name_en",
                    "deterministic_score",
                    "ai_status",
                    "ai_confidence",
                    "ai_model",
                    "final_action",
                ]
                if c in df.columns
            ]
        ]
        .head(5)
        .to_dict(orient="records"),
    }


def build_baseline_map(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    out = {}
    for _, row in df.iterrows():
        code = str(row.get("item_code") if pd.notna(row.get("item_code")) else "").strip()
        name = str(row.get("item_name") or "").strip()
        key = code if code and code.lower() != "nan" else name
        out[key] = {
            "matched_product_id": row.get("matched_product_id"),
            "matched_product_name_en": row.get("matched_product_name_en"),
            "status": row.get("status"),
        }
    return out


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs = []
    for spec in MODELS:
        runs.append(run_one(spec))

    # score
    baseline_csv = None
    for r in runs:
        if r["label"] == "baseline_no_ai" and r["summary_csv"]:
            baseline_csv = ROOT / r["summary_csv"]
            break
    baseline_map = build_baseline_map(baseline_csv) if baseline_csv else None

    scored = []
    for r in runs:
        csv_path = ROOT / r["summary_csv"] if r.get("summary_csv") else None
        s = score_summary(csv_path, baseline_map if r["label"] != "baseline_no_ai" else None)
        # for baseline, self-agreement = 100%
        if r["label"] == "baseline_no_ai" and baseline_map:
            s["agree_product_id"] = s["n_items"]
            s["disagree_vs_baseline"] = 0
        merged = {**r, **s}
        scored.append(merged)

    # rank by quality_score desc, then orderable_rate, then conf
    ranked = sorted(
        scored,
        key=lambda x: (
            x.get("quality_score") or 0,
            x.get("orderable_rate") or 0,
            x.get("ai_conf_mean") or 0,
            -(x.get("elapsed_s") or 0),
        ),
        reverse=True,
    )
    for i, row in enumerate(ranked, 1):
        row["rank"] = i

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "stamp": stamp,
        "command_base": (
            "python run.py order --config state/config.yaml --profile wardany "
            f"--excel {EXCEL} --execution-mode api --match-only --limit=30"
        ),
        "models": ranked,
    }
    json_path = OUT / f"matching_model_ranking_{stamp}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # markdown report
    lines = []
    lines.append(f"# Matching Model Ranking Report — SMALL_TEST")
    lines.append("")
    lines.append(f"**Generated:** {payload['generated_at']}")
    lines.append(f"**Profile:** `{PROFILE}`")
    lines.append(f"**Excel:** `{EXCEL}` (`--limit=30`)")
    lines.append(f"**Mode:** `api --match-only`")
    lines.append(f"**Base command:** `{payload['command_base']}`")
    lines.append("")
    lines.append("## Ranking (by matching quality score)")
    lines.append("")
    lines.append(
        "| Rank | Model | Quality | Orderable | Named | AI verified/searched | AI conf mean | Agree vs baseline | Exit | Time |"
    )
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in ranked:
        conf = row.get("ai_conf_mean")
        conf_s = f"{conf:.3f}" if conf is not None else "—"
        ai_vs = f"{row.get('ai_verified', 0)}/{row.get('ai_searched', 0)}"
        agree = row.get("agree_product_id", 0) + row.get("agree_product_name", 0)
        disagree = row.get("disagree_vs_baseline", 0)
        n = row.get("n_items") or 0
        agree_s = f"{agree}/{agree + disagree}" if (agree + disagree) else "—"
        lines.append(
            f"| {row['rank']} | `{row['label']}` | **{row.get('quality_score', 0):.1f}** | "
            f"{row.get('matched_only', 0)}/{n} ({100 * (row.get('orderable_rate') or 0):.0f}%) | "
            f"{row.get('name_nonempty', 0)}/{n} | {ai_vs} | {conf_s} | {agree_s} | "
            f"{row.get('exit_code')} | {row.get('elapsed_s')}s |"
        )
    lines.append("")
    lines.append("## Score formula")
    lines.append("")
    lines.append("- **AI runs:** `40% orderable + 20% named product + 15% agree-vs-baseline + 15% AI evidence + 10% mean confidence`")
    lines.append("- **No-AI baseline:** `50% orderable + 30% named + 20% self-agree`")
    lines.append("- Orderable = `status == matched-only` (has orderable storeProductId)")
    lines.append("- Named = non-empty `matched_product_name_en`")
    lines.append("")
    lines.append("## Per-model details")
    lines.append("")
    for row in ranked:
        lines.append(f"### {row['rank']}. `{row['label']}`")
        lines.append("")
        lines.append(f"- Provider/model pin: `{row.get('provider')}` / `{row.get('model')}`")
        lines.append(f"- Exit: `{row.get('exit_code')}` · Elapsed: **{row.get('elapsed_s')}s**")
        lines.append(f"- Artifact: `{row.get('artifact_dir')}`")
        lines.append(f"- Log: `{row.get('log')}`")
        lines.append(
            f"- Status: matched-only={row.get('matched_only')} · not-orderable={row.get('not_orderable')} · "
            f"no-results={row.get('no_results')} · other={row.get('other_status')}"
        )
        lines.append(f"- AI status counts: `{row.get('ai_status')}`")
        lines.append(
            f"- AI verified/searched/reviewed: {row.get('ai_verified')}/{row.get('ai_searched')}/{row.get('ai_reviewed')}"
        )
        lines.append(
            f"- AI conf mean / non-null: {row.get('ai_conf_mean')} / {row.get('ai_conf_non_null')}"
        )
        lines.append(f"- Models used in rows: `{row.get('models_used')}`")
        lines.append(f"- Manual review required: {row.get('manual_review_required')}")
        lines.append("")

    # note LILI drop if any
    lines.append("## Notes")
    lines.append("")
    lines.append("- Logging fix applied before runs: LogRecord-reserved `extra['name']` → `item_name` in `tawreed_order_summary.py` / `tawreed_bot_methods.py` (was crashing on first not-orderable skip).")
    lines.append("- `SMALL_TEST.xlsx` has 24 data rows; CLI processed ~23 (first row may be filtered by loader/resume).")
    lines.append("- Config primary `big-pickle` + fallbacks + health-best `mistral-medium-latest` were included.")
    lines.append(f"- Machine JSON: `{json_path.relative_to(ROOT)}`")
    lines.append("")

    md_path = OUT / f"matching_model_ranking_{stamp}.md"
    # also stable latest name
    latest_md = OUT / "matching_model_ranking_latest.md"
    latest_json = OUT / "matching_model_ranking_latest.json"
    text = "\n".join(lines) + "\n"
    md_path.write_text(text, encoding="utf-8")
    latest_md.write_text(text, encoding="utf-8")
    latest_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nREPORT: {md_path}")
    print(f"JSON:   {json_path}")
    print("RANKING:")
    for row in ranked:
        print(
            f"  #{row['rank']} {row['label']} quality={row.get('quality_score')} "
            f"orderable={row.get('matched_only')}/{row.get('n_items')} exit={row.get('exit_code')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
