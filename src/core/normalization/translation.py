"""Bilingual Arabic↔English drug-name translation.

Uses Cohere's specialized translation model as the live fallback for names
not resolved by local dictionaries or the persistent cache. Translations are
cached in two
layers:

1. **SQLite** (``state/order_runs.db`` table ``translation_cache``) —
   outlives the Python process. Reused across runs.
2. **In-process LRU** — fast path for hot items.

Environment:
    All numbered variables matching ``COHERE_API_KEY_<number>`` are tried in
    numeric order, so any number of keys can be configured.
    ``COHERE_API_KEY`` remains supported as a legacy single-key fallback.
    When no key is set, the module degrades to no-op translation.
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
MAX_BATCH_SIZE = 50
MAX_RATE_LIMIT_PER_MIN = 20

# Cohere trial keys allow 20 calls/min; each configured key gets its own
# limiter so two keys can be used independently.
def _configured_rate_limit_per_min() -> int:
    try:
        configured = int(os.environ.get("COHERE_RATE_LIMIT_PER_MIN", "20"))
    except ValueError:
        configured = MAX_RATE_LIMIT_PER_MIN
    return min(max(configured, 1), MAX_RATE_LIMIT_PER_MIN)


RATE_LIMIT_PER_MIN = _configured_rate_limit_per_min()


def _load_api_keys() -> list[str]:
    """Load all configured Cohere keys without reading dotenv files.

    Numbered keys are sorted by their numeric suffix rather than by their
    environment-variable names, so ``_2`` is tried before ``_10``.  Empty
    values and duplicate key values are ignored.  The unnumbered legacy key
    is appended after all numbered keys when it is configured.
    """
    keys: list[str] = []
    numbered: list[tuple[int, str]] = []
    for variable, raw_value in os.environ.items():
        match = re.fullmatch(r"COHERE_API_KEY_(\d+)", variable)
        if match is None:
            continue
        api_key = raw_value.strip()
        if api_key:
            numbered.append((int(match.group(1)), api_key))

    for _, api_key in sorted(numbered, key=lambda item: item[0]):
        if api_key not in keys:
            keys.append(api_key)

    legacy = os.environ.get("COHERE_API_KEY", "").strip()
    if legacy and legacy not in keys:
        keys.append(legacy)
    return keys


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
    states = _get_provider_states()
    with _breaker._lock:
        return {
            "quota_dead": _quota_dead.is_set(),
            "breaker_open": _breaker._opened_at is not None,
            "consecutive_failures": _breaker._consecutive,
            "configured_keys": len(states),
            "terminal_keys": sum(state.terminal for state in states),
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


def _get_client(api_key: str):
    """Instantiate a Cohere client for one configured key."""
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


class _ProviderState:
    def __init__(self, slot: str, api_key: str):
        self.slot = slot
        self.api_key = api_key
        self.client = None
        self.client_unavailable = False
        self.terminal = False
        self.failure_kind: str | None = None
        self.lock = threading.Lock()
        self.limiter = _RateLimiter(_configured_rate_limit_per_min())


_provider_lock = threading.Lock()
_provider_states: list[_ProviderState] | None = None
_provider_keys: tuple[str, ...] | None = None


def _reset_provider_state() -> None:
    """Reset lazy provider state; useful for isolated process/test setup."""
    global _provider_keys, _provider_states
    with _provider_lock:
        _provider_keys = None
        _provider_states = None
    _quota_dead.clear()
    _breaker.record_success()


def _get_provider_states() -> list[_ProviderState]:
    global _provider_keys, _provider_states
    keys = tuple(_load_api_keys())
    with _provider_lock:
        if _provider_states is None or _provider_keys != keys:
            _provider_keys = keys
            _provider_states = [
                _ProviderState(str(index + 1), key)
                for index, key in enumerate(keys)
            ]
            _quota_dead.clear()
        return _provider_states


def _client_for_provider(state: _ProviderState):
    with state.lock:
        if state.client_unavailable or state.terminal:
            return None
        if state.client is not None:
            return state.client
        try:
            state.client = _get_client(state.api_key)
        except Exception as error:
            if _is_terminal_key_failure(error):
                state.terminal = True
                state.failure_kind = "quota_or_key"
                logger.warning(
                    "cohere key %s disabled: %s",
                    state.slot,
                    _safe_error_text(error),
                )
            else:
                logger.warning(
                    "cohere client initialization failed for key %s: %s",
                    state.slot,
                    _safe_error_text(error),
                )
            state.client_unavailable = True
        if state.client is None:
            state.client_unavailable = True
        return state.client


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


def _error_status(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    return status if isinstance(status, int) else None


def _is_terminal_key_failure(error: Exception) -> bool:
    text = str(error).lower()
    status = _error_status(error)
    if _is_rate_limit_failure(error):
        return False
    return status in {401, 402, 403, 498} or any(
        phrase in text
        for phrase in (
            "1000 api calls",
            "/ month",
            "monthly quota",
            "quota exceeded",
            "quota exhausted",
            "maximum billing",
            "billing limit",
            "billing quota",
            "payment required",
            "invalid api key",
            "invalid api token",
            "unauthorized",
            "authentication failed",
            "expired",
        )
    )


def _is_rate_limit_failure(error: Exception) -> bool:
    text = str(error).lower()
    if any(
        phrase in text
        for phrase in (
            "1000 api calls",
            "/ month",
            "monthly quota",
            "quota exceeded",
            "quota exhausted",
            "billing limit",
            "billing quota",
        )
    ):
        return False
    return any(
        phrase in text
        for phrase in ("per minute", "/ minute", "rate limit", "429")
    )


def _safe_error_text(error: Exception) -> str:
    text = str(error).replace("\n", " ").strip()
    for api_key in _load_api_keys():
        text = text.replace(api_key, "<redacted>")
    return text[:200] or error.__class__.__name__


def _mark_provider_terminal(state: _ProviderState, error: Exception) -> None:
    with state.lock:
        state.terminal = True
        state.failure_kind = "quota_or_key"
    logger.warning(
        "cohere key %s disabled: %s", state.slot, _safe_error_text(error)
    )


def _configured_model() -> str:
    return (
        os.environ.get("COHERE_TRANSLATION_MODEL", PRIMARY_MODEL).strip()
        or PRIMARY_MODEL
    )


def _chat(client, model: str, prompt: str):
    method = getattr(client, "chat_v2", None) or getattr(client, "chat", None)
    if method is None:
        raise AttributeError("Cohere client has no chat method")
    return method(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )


def _parse_batch_response(text: str | None, count: int) -> list[str | None]:
    if not text:
        return [None] * count
    by_index: dict[int, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*(\d+)\s*[.)-]\s*(.*?)\s*$", line)
        if match and match.group(2):
            index = int(match.group(1))
            if 1 <= index <= count:
                by_index[index] = match.group(2).strip()
    return [by_index.get(index) for index in range(1, count + 1)]


def _call_cohere_batch(model: str, texts: list[str]) -> list[str | None]:
    """Translate one batch, failing over only on terminal key errors."""
    if not texts:
        return []
    if not _breaker.allow():
        return [None] * len(texts)
    states = _get_provider_states()
    if not states:
        return [None] * len(texts)
    numbered_lines = "\n".join(
        f"{i + 1}. {text}" for i, text in enumerate(texts)
    )
    prompt = (
        f"{_PROMPT}\n\n{numbered_lines}\n\n"
        f"Reply with exactly {len(texts)} lines in the format `<index>. <translation>`."
    )
    for state in states:
        client = _client_for_provider(state)
        if client is None:
            continue
        attempts = 0
        while attempts < 2:
            attempts += 1
            state.limiter.acquire()
            try:
                response = _chat(client, model, prompt)
                parsed = _parse_batch_response(
                    _extract_text(response.message.content), len(texts)
                )
            except Exception as error:
                logger.warning(
                    "cohere batch failed for key %s: %s",
                    state.slot,
                    _safe_error_text(error),
                )
                if _is_terminal_key_failure(error):
                    _mark_provider_terminal(state, error)
                    break
                if _is_rate_limit_failure(error):
                    if attempts == 1:
                        time.sleep(1.0)
                        continue
                    # A per-minute limit is temporary for this key. Keep it
                    # healthy and let the next batch try it again; do not
                    # burn the other key as a quota failover.
                    return [None] * len(texts)
                _breaker.record_failure()
                return [None] * len(texts)
            _breaker.record_success()
            return parsed
    if states and all(state.terminal or state.client_unavailable for state in states):
        _quota_dead.set()
    return [None] * len(texts)


def _call_cohere(model: str, text: str) -> str | None:
    results = _call_cohere_batch(model, [text])
    return results[0] if results else None


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
    primary = _call_cohere(_configured_model(), cleaned)
    if primary and cache is not None:
        try:
            cache.put_many({cleaned: primary}, model=_configured_model())
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


class CachedTranslations(dict[str, str]):
    """Cached translations carrying their source model without changing dict callers."""

    def __init__(self, translations: dict[str, str], models: dict[str, str]) -> None:
        super().__init__(translations)
        self.models = models


def ar_to_en_many_cached_only(names: list[str]) -> dict[str, str]:
    """Return cached translations for many names without contacting a provider."""
    original_to_clean: dict[str, str] = {}
    for name in names:
        cleaned = _clean(name)
        if cleaned:
            original_to_clean[name] = cleaned
    if not original_to_clean:
        return {}
    cache = _persistent()
    if cache is None:
        return {}
    try:
        cached = cache.get_many_with_models(list(set(original_to_clean.values())))
    except AttributeError:
        cached = {
            key: (translation, "")
            for key, translation in cache.get_many(
                list(set(original_to_clean.values()))
            ).items()
        }
    except Exception:
        return {}
    translations = {
        original: cached.get(normalize_key_for_lru(cleaned), ("", ""))[0]
        for original, cleaned in original_to_clean.items()
        if cached.get(normalize_key_for_lru(cleaned), ("", ""))[0]
    }
    models = {
        original: cached.get(normalize_key_for_lru(cleaned), ("", ""))[1]
        for original, cleaned in original_to_clean.items()
        if cached.get(normalize_key_for_lru(cleaned), ("", ""))[0]
    }
    return CachedTranslations(translations, models)


def ar_to_en_many(
    names: list[str], *, batch_size: int | None = None
) -> dict[str, str]:
    """Translate many Arabic names, using the persistent cache and
    batched Cohere calls for the remainder.

    Returns a dict ``{raw_ar: en_text}``; missing entries are absent
    from the result.
    """
    names_by_key: dict[str, list[str]] = {}
    for name in names:
        cleaned = _clean(name)
        if cleaned:
            key = normalize_key_for_lru(cleaned)
            if key:
                names_by_key.setdefault(key, []).append(cleaned)
    if not names_by_key:
        return {}
    result: dict[str, str] = {}
    cache = _persistent()
    if cache is not None:
        try:
            cached = cache.get_many(
                [aliases[0] for aliases in names_by_key.values()]
            )
        except Exception:
            cached = {}
    else:
        cached = {}

    pending: list[tuple[str, list[str]]] = []
    for key, aliases in names_by_key.items():
        cached_translation = cached.get(key)
        if cached_translation:
            for alias in aliases:
                result[alias] = cached_translation
        else:
            pending.append((key, aliases))

    if pending:
        if batch_size is None:
            try:
                batch_size = int(os.environ.get("COHERE_BATCH_SIZE", "50"))
            except ValueError:
                batch_size = MAX_BATCH_SIZE
        batch_size = min(max(batch_size, 1), MAX_BATCH_SIZE)
        for i in range(0, len(pending), batch_size):
            chunk = pending[i : i + batch_size]
            chunk_names = [aliases[0] for _, aliases in chunk]
            batched = _call_cohere_batch(_configured_model(), chunk_names)
            cache_entries: dict[str, str] = {}
            for (_, aliases), en in zip(chunk, batched):
                for alias in aliases:
                    result[alias] = en or ""
                if en:
                    cache_entries[aliases[0]] = en
            if cache is not None:
                try:
                    cache.put_many(cache_entries, model=_configured_model())
                except Exception:
                    pass
    return result
