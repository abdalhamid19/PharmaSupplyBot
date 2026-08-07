#!/usr/bin/env python3
"""
فحص حي لكل نموذج AI متاح: يبعت طلباً حقيقياً لكل (provider, model) فريد
ويتحقق أن الـ API يرد بـ 200 + JSON صالح.

- يحمّل `.env` للبيئة.
- يجمع كل الـ attempts من `ai_rotation.configured_attempts()`.
- لكل نموذج فريد: طلب حقيقي عبر `ai_health_test_execution.execute_one`
  مع الـ base_url الصحيح لمزوّده.
- يكتب تقرير Markdown كامل في `docs/reports/ai_models_live_check.md`.

التحذير: ده يستهلك النقاط (quota) عند كل provider — طلب واحد لكل نموذج.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

import aiohttp

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from src.core.drug_matching.ai.ai_health_test_execution import execute_one
from src.core.drug_matching.ai.ai_health_test_constants import AIKey
from src.core.drug_matching.ai.ai_rotation import configured_attempts

REPORT_DIR = Path(__file__).resolve().parent.parent / "docs" / "reports"
REPORT_FILE = REPORT_DIR / "ai_models_live_check.md"

TIMEOUT_S = 25.0
MAX_TOKENS = 64
CONCURRENCY = 6


def load_env() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        print("[X] .env غير موجود")
        sys.exit(1)
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v:
                os.environ.setdefault(k, v)


def unique_models() -> list[dict]:
    """مكوّنات (provider, model) الفريدة مع أول key متاح و base_url."""
    attempts = configured_attempts()
    seen: dict[tuple[str, str], dict] = {}
    for a in attempts:
        key = (a.provider, a.model)
        if key not in seen:
            seen[key] = {
                "provider": a.provider,
                "model": a.model,
                "base_url": a.base_url,
                "key_name": a.key_name,
                "api_key": a.api_key,
                "rotation_tier": a.rotation_tier,
            }
    return list(seen.values())


async def run_all(items: list[dict]) -> list[dict]:
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:

        async def guarded(item: dict) -> dict:
            key = AIKey(name=item["key_name"], value=item["api_key"])
            async with sem:
                res = await execute_one(
                    session,
                    key,
                    item["model"],
                    mode="json",
                    timeout_s=TIMEOUT_S,
                    max_tokens=MAX_TOKENS,
                    base_url=item["base_url"],
                )
            res["provider"] = item["provider"]
            res["rotation_tier"] = item["rotation_tier"]
            return res

        return await asyncio.gather(*(guarded(i) for i in items))


def build_report(results: list[dict], total: int) -> str:
    ok = [r for r in results if r.get("ok")]
    http_ok = [r for r in results if r.get("http_status") == 200]
    failed = [r for r in results if not r.get("ok")]

    by_provider: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "ok": 0, "http_200": 0}
    )
    for r in results:
        p = by_provider[r["provider"]]
        p["total"] += 1
        if r.get("ok"):
            p["ok"] += 1
        if r.get("http_status") == 200:
            p["http_200"] += 1

    lines: list[str] = [
        "# الفحص الحي لنماذج الذكاء الاصطناعي (Live Check)",
        "",
        "## النتيجة المختصرة",
        "",
        "| القياس | القيمة |",
        "|---|---|",
        f"| النماذج المفحوصة | **{total}** |",
        f"| استجاب 200 (HTTP) | **{len(http_ok)}** |",
        f"| JSON صالح (ok) | **{len(ok)}** |",
        f"| فشل | **{len(failed)}** |",
        "",
        "### لكل مزوّد",
        "",
        "| مزوّد | فحص | 200 | ok |",
        "|---|---|---|---|",
    ]
    for prov in sorted(by_provider):
        p = by_provider[prov]
        lines.append(
            f"| `{prov}` | {p['total']} | {p['http_200']} | {p['ok']} |"
        )

    lines += [
        "",
        "## تفاصيل الفشل",
        "",
        "| مزوّد | النموذج | حالة | نوع الخطأ | رسالة |",
        "|---|---|---|---|---|",
    ]
    if not failed:
        lines.append("_لا توجد حالات فشل._")
    for r in failed:
        err = (r.get("error_type") or "").replace("|", "\\|")
        msg = (r.get("error_message") or "").replace("|", "\\|")[:120]
        lines.append(
            f"| `{r['provider']}` | `{r['model']}` | "
            f"{r.get('http_status')} | {err} | {msg} |"
        )

    lines += [
        "",
        "## كل النماذج (النتيجة)",
        "",
        "| مزوّد | Tier | النموذج | الحالة |",
        "|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: (x["provider"], x["model"])):
        status = "✅" if r.get("ok") else "❌"
        lines.append(
            f"| `{r['provider']}` | {r.get('rotation_tier', '')} | "
            f"`{r['model']}` | {status} |"
        )
    return "\n".join(lines)


def main() -> int:
    load_env()
    items = unique_models()
    print(f"🚀 فحص حي لـ {len(items)} نموذج (طلبات حقيقية)...\n")

    results = asyncio.run(run_all(items))

    ok = sum(1 for r in results if r.get("ok"))
    http = sum(1 for r in results if r.get("http_status") == 200)
    print(f"[done] 200: {http}/{len(items)} | ok(JSON): {ok}/{len(items)}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(build_report(results, len(items)), encoding="utf-8")
    print(f"\n✅ اُنتج التقرير: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
