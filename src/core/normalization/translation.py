"""Bilingual Arabic↔English drug-name translation.

Uses Cohere's specialized translation model as the primary engine, with a
general-purpose LLM as a fallback for cases the translation model handles
poorly (e.g. very noisy transcriptions). Translations are cached in two
layers:

1. **SQLite** (``state/order_runs.db`` table ``translation_cache``) —
   outlives the Python process. Reused across runs.
2. **In-process LRU** — fast path for hot items.

Environment:
    ``COHERE_API_KEY`` must be set. When missing, the module degrades to
    no-op identity translation so the rest of the matching pipeline can
    still run.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from functools import lru_cache

logger = logging.getLogger(__name__)


PRIMARY_MODEL = "command-a-translate-08-2025"
FALLBACK_MODEL = "command-a-plus-05-2026"

# Cohere trial key is 20 calls/min; we use a token bucket so we don't
# burn through it. The default leaves headroom for other API users.
RATE_LIMIT_PER_MIN = int(os.environ.get("COHERE_RATE_LIMIT_PER_MIN", "15"))


class _ProviderBreaker:
    """Open on repeated consecutive provider failures; half-open after cooldown.

    When open, :meth:`allow` returns False and callers must not hit the
    network. After ``cooldown_s`` the breaker half-opens (one probe call
    is allowed); a failure re-opens it, a success fully closes it.
    """

    def __init__(self, threshold: int = 3, cooldown_s: float = 300.0):
        self.threshold = max(threshold, 1)
        self.cooldown_s = cooldown_s
        self._consecutive = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at >= self.cooldown_s:
                self._opened_at = None
                self._consecutive = self.threshold - 1
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._consecutive = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive += 1
            if self._consecutive >= self.threshold and self._opened_at is None:
                self._opened_at = time.monotonic()
                logger.error(
                    "translation provider breaker OPEN after %d consecutive failures "
                    "(cooldown %.0fs) — live translation disabled until then",
                    self._consecutive,
                    self.cooldown_s,
                )


_breaker = _ProviderBreaker()
# Terminal condition: the Cohere trial key's *monthly* quota is exhausted.
# Unlike the per-minute limit this does not recover by waiting, so once
# detected we stop calling entirely for the life of the process.
_quota_dead = threading.Event()


def provider_status() -> dict[str, bool | int]:
    """Expose live-translation availability for run summaries."""
    with _breaker._lock:
        return {
            "quota_dead": _quota_dead.is_set(),
            "breaker_open": _breaker._opened_at is not None,
            "consecutive_failures": _breaker._consecutive,
        }


_PROMPT = (
    "Translate Egyptian Arabic pharmaceutical product names to English. "
    "Keep brand names as transliterated Latin letters "
    "(e.g. بنادول -> Panadol). Translate descriptive Arabic words "
    "(كريم=cream, أقراص=tablets, كبسولة=capsule, شراب=syrup, "
    "قطرة=drops, حقن=injection, مرهم=ointment, جل=gel, بخاخ=spray, "
    "لبن=milk, بودرة=powder, لبوس=suppository). Keep metric units "
    "in standard abbreviations (مجم=mg, مل=ml, جم=g/mcg=mcg, "
    "%=percent)."
)


def _get_client():
    """Lazily import cohere and instantiate the v2 client."""
    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        return None
    try:
        import cohere  # type: ignore
    except ImportError:
        logger.warning("cohere package not installed; translation disabled")
        return None
    try:
        return cohere.ClientV2(api_key=api_key)
    except (AttributeError, TypeError):
        return cohere.Client(api_key)


_client_lock = threading.Lock()
_client = None


def _client_singleton():
    global _client
    with _client_lock:
        if _client is None:
            _client = _get_client()
    return _client


class _RateLimiter:
    """Thread-safe token bucket: at most N calls per 60 seconds."""

    def __init__(self, per_minute: int):
        self.per_minute = max(per_minute, 1)
        self.timestamps: list[float] = []
        self.lock = threading.Lock()

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            self.timestamps = [t for t in self.timestamps if now - t < 60]
            while len(self.timestamps) >= self.per_minute:
                sleep_for = 60 - (now - self.timestamps[0]) + 0.1
                self.lock.release()
                try:
                    if sleep_for > 0:
                        time.sleep(sleep_for)
                finally:
                    self.lock.acquire()
                now = time.monotonic()
                self.timestamps = [t for t in self.timestamps if now - t < 60]
            self.timestamps.append(time.monotonic())


_limiter = _RateLimiter(RATE_LIMIT_PER_MIN)


def _extract_text(content) -> str | None:
    """Pull plain text out of a v2 response.content payload."""
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        for part in content:
            text = getattr(part, "text", None)
            if text is None and isinstance(part, dict):
                text = part.get("text")
            if text:
                return str(text).strip() or None
        return None
    text = getattr(content, "text", None)
    return str(text).strip() if text else None


def _classify_provider_failure(error: Exception) -> None:
    """Flag terminal quota exhaustion so callers can stop trying.

    Cohere returns 429 with two distinct bodies:
    - "limited to 20 API calls / minute"  → transient, the rate limiter
      paces us; no special handling needed.
    - "limited to 1000 API calls / month" → terminal for the process:
      waiting cannot help. Sets ``_quota_dead``.
    """
    text = str(error)
    if "/ month" in text or "1000 API calls" in text:
        if not _quota_dead.is_set():
            logger.error(
                "cohere monthly quota exhausted — live translation disabled "
                "for the rest of this process (cache-only mode)"
            )
        _quota_dead.set()


def _call_cohere(model: str, text: str) -> str | None:
    if _quota_dead.is_set() or not _breaker.allow():
        return None
    co = _client_singleton()
    if co is None:
        return None
    _limiter.acquire()
    try:
        if hasattr(co, "chat_v2"):
            response = co.chat_v2(
                model=model,
                messages=[{"role": "user", "content": f"{_PROMPT}\n\nName: {text}"}],
                temperature=0,
            )
        else:
            response = co.chat(
                model=model,
                messages=[{"role": "user", "content": f"{_PROMPT}\n\nName: {text}"}],
                temperature=0,
            )
        text_out = _extract_text(response.message.content)
        if text_out:
            _breaker.record_success()
        return text_out
    except Exception as error:
        logger.warning("cohere %s call failed: %s", model, error)
        _classify_provider_failure(error)
        _breaker.record_failure()
        return None


def _call_cohere_batch(model: str, texts: list[str]) -> list[str | None]:
    """Translate up to ``len(texts)`` names in a single Cohere call.

    Returns a list parallel to ``texts``; missing lines in the response
    are returned as ``None`` so the caller can fall back to single
    calls for just those names.
    """
    if _quota_dead.is_set() or not _breaker.allow():
        return [None] * len(texts)
    co = _client_singleton()
    if co is None or not texts:
        return [None] * len(texts)
    _limiter.acquire()
    numbered_lines = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    user_prompt = (
        f"{_PROMPT}\n\n{numbered_lines}\n\n"
        f"Reply with exactly {len(texts)} lines in the format `<index>. <translation>`."
    )
    try:
        if hasattr(co, "chat_v2"):
            response = co.chat_v2(
                model=model,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0,
            )
        else:
            response = co.chat(
                model=model,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0,
            )
        text = _extract_text(response.message.content)
        if text:
            _breaker.record_success()
    except Exception as error:
        logger.warning("cohere %s batch failed: %s", model, error)
        _classify_provider_failure(error)
        _breaker.record_failure()
        return [None] * len(texts)
    if not text:
        return [None] * len(texts)

    by_index: dict[int, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        head, _, rest = line.partition(".")
        head = head.strip()
        rest = rest.strip()
        if not rest:
            continue
        if head.isdigit():
            by_index[int(head)] = rest
        elif head == "" and rest[:1].isdigit():
            digits = ""
            for ch in rest:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                by_index[int(digits)] = rest[len(digits):].lstrip(".) ").strip()

    return [by_index.get(i + 1) for i in range(len(texts))]


_WHITESPACE_RE = re.compile(r"\s+")


def _clean(s: str) -> str:
    return _WHITESPACE_RE.sub(" ", s).strip()


_cache_lock = threading.Lock()
_persistent_cache = None


def _persistent():
    """Lazy-init the persistent SQLite translation cache."""
    global _persistent_cache
    if _persistent_cache is not None:
        return _persistent_cache
    with _cache_lock:
        if _persistent_cache is not None:
            return _persistent_cache
        try:
            from src.core.database.translation_cache import TranslationCache
            _persistent_cache = TranslationCache()
        except Exception as error:
            logger.warning("translation cache init failed: %s", error)
            return None
    return _persistent_cache


@lru_cache(maxsize=20000)
def _lru_translate(name: str) -> str:
    """In-process cached translation, after the persistent lookup.

    Returns ``""`` when the translation failed (cache miss and no live
    provider available). Callers must treat empty as failure; returning
    the Arabic input as its own "translation" silently corrupted the
    scoring pipeline (see docs/postmortem/01 §R3).
    """
    if not name:
        return name
    cleaned = _clean(name)
    cache = _persistent()
    if cache is not None:
        try:
            hits = cache.get_many([cleaned])
            if hits:
                return hits[normalize_key_for_lru(cleaned)]
        except Exception:
            pass
    if _quota_dead.is_set() or not _breaker.allow():
        return ""
    primary = _call_cohere(PRIMARY_MODEL, cleaned)
    if primary is None and not _quota_dead.is_set() and _breaker.allow():
        primary = _call_cohere(FALLBACK_MODEL, cleaned)
    if primary and cache is not None:
        try:
            cache.put_many({cleaned: primary}, model=PRIMARY_MODEL)
        except Exception:
            pass
    return primary or ""


def normalize_key_for_lru(text: str) -> str:
    """Mirror :func:`translation_cache.normalize_key` for the LRU path.

    The persistent lookup key differs from the LRU cache key, so we
    look up using the same key the DB row was indexed on.
    """
    try:
        from src.core.database.translation_cache import normalize_key
        return normalize_key(text)
    except Exception:
        return text


def ar_to_en(name: str) -> str:
    """Translate one Arabic drug name to English.

    Returns ``""`` on failure (no cached translation and the live
    provider is unavailable/disabled) — never the Arabic input itself.
    """
    if not name:
        return name
    cleaned = _clean(name)
    if not cleaned:
        return name
    return _lru_translate(cleaned)


def ar_to_en_cached_only(name: str) -> str:
    """Return the cached translation for ``name`` or ``""``.

    Never contacts Cohere — used by interactive matching paths so a
    per-candidate lookup can never burn API quota mid-run. Live
    translation belongs to the batch pre-translate CLI.
    """
    if not name:
        return ""
    cleaned = _clean(name)
    if not cleaned:
        return ""
    cache = _persistent()
    if cache is None:
        return ""
    try:
        hits = cache.get_many([cleaned])
        return hits.get(normalize_key_for_lru(cleaned), "")
    except Exception:
        return ""


def ar_to_en_many_cached_only(names: list[str]) -> dict[str, str]:
    """Return cached translations for many names without contacting a provider."""
    original_to_clean = {name: _clean(name) for name in names if _clean(name)}
    if not original_to_clean:
        return {}
    cache = _persistent()
    if cache is None:
        return {}
    try:
        cached = cache.get_many(list(set(original_to_clean.values())))
    except Exception:
        return {}
    return {
        original: cached.get(normalize_key_for_lru(cleaned), "")
        for original, cleaned in original_to_clean.items()
        if cached.get(normalize_key_for_lru(cleaned), "")
    }


def ar_to_en_many(names: list[str]) -> dict[str, str]:
    """Translate many Arabic names, using the persistent cache and
    batched Cohere calls for the remainder.

    Returns a dict ``{raw_ar: en_text}``; missing entries are absent
    from the result.
    """
    cleaned = [_clean(n) for n in names]
    cleaned = [c for c in cleaned if c]
    if not cleaned:
        return {}
    result: dict[str, str] = {}
    cache = _persistent()
    if cache is not None:
        try:
            cached = cache.get_many(cleaned)
        except Exception:
            cached = {}
    else:
        cached = {}

    pending: list[str] = []
    for raw in cleaned:
        if raw in cached:
            result[raw] = cached[raw]
        else:
            pending.append(raw)

    if pending:
        BATCH_SIZE = int(os.environ.get("COHERE_BATCH_SIZE", "50"))
        for i in range(0, len(pending), BATCH_SIZE):
            chunk = pending[i : i + BATCH_SIZE]
            batched = _call_cohere_batch(PRIMARY_MODEL, chunk)
            for raw, en in zip(chunk, batched):
                if en is None:
                    en = (
                        _call_cohere(FALLBACK_MODEL, raw)
                        if not _quota_dead.is_set() and _breaker.allow()
                        else None
                    )
                result[raw] = en or ""
            if cache is not None:
                try:
                    cache.put_many(
                        {raw: en for raw, en in zip(chunk, batched) if en},
                        model=PRIMARY_MODEL,
                    )
                except Exception:
                    pass
    return result
