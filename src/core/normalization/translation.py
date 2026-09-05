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


def _call_cohere(model: str, text: str) -> str | None:
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
        return _extract_text(response.message.content)
    except Exception as error:
        logger.warning("cohere %s call failed: %s", model, error)
        return None


def _call_cohere_batch(model: str, texts: list[str]) -> list[str | None]:
    """Translate up to ``len(texts)`` names in a single Cohere call.

    Returns a list parallel to ``texts``; missing lines in the response
    are returned as ``None`` so the caller can fall back to single
    calls for just those names.
    """
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
    except Exception as error:
        logger.warning("cohere %s batch failed: %s", model, error)
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
    """In-process cached translation, after the persistent lookup."""
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
    primary = _call_cohere(PRIMARY_MODEL, cleaned)
    if primary is None:
        primary = _call_cohere(FALLBACK_MODEL, cleaned)
    if primary and cache is not None:
        try:
            cache.put_many({cleaned: primary}, model=PRIMARY_MODEL)
        except Exception:
            pass
    return primary or cleaned


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
    """Translate one Arabic drug name to English."""
    if not name:
        return name
    cleaned = _clean(name)
    if not cleaned:
        return name
    return _lru_translate(cleaned)


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
                    en = _call_cohere(FALLBACK_MODEL, raw) or raw
                result[raw] = en
            if cache is not None:
                try:
                    cache.put_many(
                        {raw: en for raw, en in zip(chunk, batched) if en},
                        model=PRIMARY_MODEL,
                    )
                except Exception:
                    pass
    return result
