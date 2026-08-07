#!/usr/bin/env python3
"""
اختبار استكشاف نظام Tiering لكل مزود خدمة والنماذج المتاحة لكل منهم (real API reads).

- يحمّل `.env` للبيئة (عشان `configured_attempts` يقرأ الـ keys فعلاً).
- يجمع كل الـ attempts من `ai_rotation` لكل provider.
- يلخص النماذج الفريدة لكل provider مع الـ tier/quality-rank.
- يطبع ملخصاً في الـ terminal ويكتب تقرير Markdown كامل في `docs/reports/ai_model_tiers.md`.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from src.core.drug_matching.ai.ai_rotation import configured_attempts

REPORT_DIR = Path(__file__).resolve().parent.parent / "docs" / "reports"
REPORT_FILE = REPORT_DIR / "ai_model_tiers.md"


def load_env() -> dict[str, list[str]]:
    env_path = Path(".env")
    if not env_path.exists():
        print("[X] .env غير موجود")
        return {}
    keys: dict[str, list[str]] = defaultdict(list)
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if not k:
                continue
            if v:
                os.environ.setdefault(k, v)
            keys[k].append(v)
    return dict(keys)


def tier_emoji(tier: int) -> str:
    return {1: "✅", 2: "⚠️", 3: "❌"}.get(tier, "⚪")


def build_report() -> str:
    keys = load_env()

    raw: list = configured_attempts()
    attempts = list(raw)
    if not attempts:
        return (
            "# تقرير استكشاف نماذج الذكاء الاصطناعي\n\n"
            "لم يتم العثور على أي attempts. تأكد من كشف `ai.providers.*` "
            "في `state/config.yaml` أو `config.yaml`، ومن أن مفاتيح `.env` "
            "موجودة وقائمة في `env_keys` لكل provider.\n"
            "> الـ attempts تُبنى عبر `ai_rotation.configured_attempts()`."
        )

    # نماذج فريدة لكل (provider, model) -> أدنى tier (الأفضل).
    uniq: dict[str, dict[str, int]] = defaultdict(dict)
    for a in attempts:
        cur = uniq[a.provider].get(a.model)
        if cur is None or a.rotation_tier < cur:
            uniq[a.provider][a.model] = a.rotation_tier

    total_attempts = len(attempts)
    total_unique = sum(len(m) for m in uniq.values())
    tier_dist: defaultdict[int, int] = defaultdict(int)
    for models in uniq.values():
        for t in models.values():
            tier_dist[t] += 1

    lines: list[str] = [
        "# تقرير استكشاف نماذج الذكاء الاصطناعي وترتيبها (Tiers)",
        "",
        "## نظرة عامة",
        "",
        "| القياس | القيمة |",
        "|---|---|",
        f"| إجمالي المحاولات (attempts) | **{total_attempts}** |",
        f"| المفتاحـُ الواجب توافره | **يقرأ من `.env` عبر dotenv** |",
        f"| عدد مزوّدي الخدمة | **{len(uniq)}** |",
        f"| النماذج الفريدة الإجمالية | **{total_unique}** |",
        "",
        "### توزيع النماذج الفريدة حسب الـ Tier",
        "",
        "| Tier | الوصف | عدد النماذج |",
        "|---|---|---|",
        f"| **Tier 1** | الأقوى (أول ثُلث لكل قائمة) | {tier_dist.get(1, 0)} |",
        f"| **Tier 2** | المتوسط | {tier_dist.get(2, 0)} |",
        f"| **Tier 3** | الأضعف (آخر ثُلث) | {tier_dist.get(3, 0)} |",
        "",
        "> يُحسب الـ tier لكل نموذج من ترتيبه داخل قائمة نماذج المزوّد",
        "> (مع `_model_tier` في `ai_rotation.py`) — تقسيم متساوي لثلاثة أثلاث.",
        "",
    ]

    for provider in sorted(uniq.keys()):
        models_map = uniq[provider]
        lines.append(f"## `{provider}`")
        lines.append("")
        lines.append(f"- **النماذج الفريدة**: {len(models_map)}")
        lines.append("")
        lines.append("| Tier | النموذج |")
        lines.append("|---|------|")
        for model in sorted(models_map):
            lines.append(
                f"| {tier_emoji(models_map[model])} **Tier {models_map[model]}** | `{model}` |"
            )
        lines.append("")

    lines += [
        "---",
        "",
        "## كيف يُحسب الـ Tier لكل نموذج؟",
        "",
        "```python",
        "def _model_tier(rank, model_count):",
        "    if model_count <= 0: return 3",
        "    first_end  = (model_count + 2) // 3",
        "    second_end = (model_count * 2 + 2) // 3",
        "    return 1 if rank <= first_end else 2 if rank <= second_end else 3",
        "```",
        "",
        "أي الترتيب `rank` (1-indexed) للنموذج داخل قائمة",
        "`ai.providers.<name>.models` من `config.yaml`.",
    ]

    return "\n".join(lines)


def main() -> int:
    report = build_report()

    # طباعة ملخص في الـ terminal.
    print("🚀 استكشاف Tiering والنماذج المتاحة:\n")
    if "لم يتم العثور" in report:
        print(report.split("---")[0])
        print("\n[!] لم تُولَّد أي نماذج. اطّلع على رسالة الخطأ أعلاه.")
    else:
        # نظهر الجزء الثاني (النظرة العامة + الجداول) بتاع كل provider.
        print(report.split("## كيف يُحسب")[0])

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"\n✅ اُنتج التقرير: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())