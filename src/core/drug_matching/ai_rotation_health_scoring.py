"""Health scoring and ranking logic for rotated AI attempts."""


def rank_health_rows(rows: list[dict]) -> list[dict]:
    from .ai_rotation_health_status import health_status, fallback_tier, rotation_recommendation, _quota_remaining
    
    ranked = sorted(rows, key=lambda r: _health_sort_key(r, fallback_tier, _quota_remaining))
    for idx, row in enumerate(ranked, start=1):
        row["health_status"] = health_status(row)
        row["fallback_tier"] = fallback_tier(row)
        row["rotation_recommendation"] = rotation_recommendation(row)
        row["rotation_rank"] = idx
        row["rotation_score"] = _rotation_score(row, _quota_remaining)
    return ranked


def _health_sort_key(row: dict, fallback_tier_fn, quota_remaining_fn):
    tier = fallback_tier_fn(row)
    return (
        tier,
        int(row.get("rotation_tier") or 3),
        int(row.get("quality_rank") or 999),
        -quota_remaining_fn(row),
        float(row.get("elapsed_s") or 9999),
        str(row.get("provider", "")),
    )


def _rotation_score(row: dict, quota_remaining_fn) -> float:
    if not row.get("ok"):
        return 0.0
    tier_bonus = max(0.0, 40.0 - int(row.get("rotation_tier") or 3) * 10.0)
    quality = max(0.0, 80.0 - int(row.get("quality_rank") or 100) * 5)
    quota = min(quota_remaining_fn(row), 1000.0) / 20.0
    latency = max(0.0, 20.0 - float(row.get("elapsed_s") or 20))
    return round(tier_bonus + quality + quota + latency, 2)
