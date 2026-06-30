"""Selection logic for rotated AI attempts based on health data."""

from .ai_rotation import AIModelAttempt
from .ai_rotation_health_status import health_status, _PERMANENT_FAILURES


def select_preflight_attempts(
    attempts: tuple[AIModelAttempt, ...],
    budget: int,
    tier_limit: int = 3,
) -> tuple[AIModelAttempt, ...]:
    """Select attempts for preflight health checks within budget and tier limit."""
    if budget <= 0:
        return ()
    eligible = [
        attempt for attempt in attempts
        if attempt.rotation_tier <= max(1, tier_limit)
    ]
    selected: list[AIModelAttempt] = []
    for tier in sorted({attempt.rotation_tier for attempt in eligible}):
        tier_attempts = [
            attempt for attempt in eligible if attempt.rotation_tier == tier
        ]
        for attempt in _provider_round_robin(tier_attempts):
            selected.append(attempt)
            if len(selected) >= budget:
                return tuple(selected)
    return tuple(selected)


def attempts_from_partial_health(
    attempts: tuple[AIModelAttempt, ...],
    rows: list[dict],
) -> tuple[AIModelAttempt, ...]:
    """Select attempts based on partial health data, prioritizing healthy ones."""
    by_key = {attempt.safe_tuple(): attempt for attempt in attempts}
    row_keys = {
        _row_key(row) for row in rows if row.get("mode") == "json"
    }
    healthy = []
    transient = []
    permanent = []
    for row in rows:
        if row.get("mode") != "json":
            continue
        attempt = by_key.get(_row_key(row))
        if not attempt:
            continue
        if row.get("ok"):
            healthy.append(attempt)
        elif health_status(row) in _PERMANENT_FAILURES:
            permanent.append(attempt)
        else:
            transient.append(attempt)
    untested = [attempt for attempt in attempts if attempt.safe_tuple() not in row_keys]
    return tuple(
        _dedupe_attempts(healthy + untested + transient + permanent),
    )


def cached_working_attempts(
    attempts: tuple[AIModelAttempt, ...],
    rows: list[dict],
    limit: int,
) -> tuple[AIModelAttempt, ...]:
    """Return cached working attempts from health data up to the limit."""
    if limit <= 0:
        return ()
    by_key = {attempt.safe_tuple(): attempt for attempt in attempts}
    out = []
    # Simple ranking by ok status first, then elapsed time
    sorted_rows = sorted(
        [r for r in rows if r.get("mode") == "json"],
        key=lambda r: (not r.get("ok"), float(r.get("elapsed_s") or 9999))
    )
    for row in sorted_rows:
        if row.get("mode") != "json" or not row.get("ok"):
            continue
        attempt = by_key.get(_row_key(row))
        if not attempt:
            continue
        out.append(attempt)
        if len(out) >= limit:
            break
    return tuple(_dedupe_attempts(out))


def attempts_from_health(
    attempts: tuple[AIModelAttempt, ...],
    rows: list[dict],
) -> tuple[AIModelAttempt, ...]:
    """Select attempts based on full health data, returning healthy or fallback attempts."""
    by_key = {attempt.safe_tuple(): attempt for attempt in attempts}
    healthy = []
    fallback = []
    for row in rows:
        if row.get("mode") != "json":
            continue
        key = (
            str(row.get("provider", "")),
            str(row.get("key_suffix", "")),
            str(row.get("model", "")),
        )
        attempt = by_key.get(key)
        if not attempt:
            continue
        if row.get("ok"):
            healthy.append(attempt)
        else:
            fallback.append(attempt)
    return tuple(healthy or fallback)


def _provider_round_robin(
    attempts: list[AIModelAttempt],
) -> list[AIModelAttempt]:
    grouped: dict[str, list[AIModelAttempt]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.provider, []).append(attempt)
    out = []
    providers = sorted(grouped)
    while providers:
        next_providers = []
        for provider in providers:
            values = grouped[provider]
            out.append(values.pop(0))
            if values:
                next_providers.append(provider)
        providers = next_providers
    return out


def _row_key(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("provider", "")),
        str(row.get("key_suffix", "")),
        str(row.get("model", "")),
    )


def _dedupe_attempts(
    attempts: list[AIModelAttempt],
) -> list[AIModelAttempt]:
    seen = set()
    out = []
    for attempt in attempts:
        key = attempt.safe_tuple()
        if key in seen:
            continue
        seen.add(key)
        out.append(attempt)
    return out
