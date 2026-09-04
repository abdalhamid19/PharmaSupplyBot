"""Bilingual Arabic↔English drug-name translation.

Uses Cohere's specialized translation model as the primary engine, with a
general-purpose LLM as a fallback for cases the translation model handles
poorly (e.g. very noisy transcriptions). The translation is cached in
process to keep latency low for repeated runs.

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
    "Translate this Egyptian Arabic pharmaceutical product name to "
    "English. Keep brand names as transliterated Latin letters "
    "(e.g. بنادول -> Panadol), translate descriptive Arabic words "
    "(كريم=cream, أقراص=tablets, كبسولة=capsule, شراب=syrup, "
    "قطرة=drops, حقن=injection, مرهم=ointment, جل=gel, بخاخ=spray, "
    "لبن=milk, بودرة=powder, لبوس=suppository), and keep metric units "
    "in standard abbreviations (مجم=mg, مل=ml, جم=g/mcg=mcg, "
    "%=percent). Return ONLY the translated name, no commentary."
)


def _get_client():
    """Lazily import cohere and instantiate the v2 client.

    Returns ``None`` when ``COHERE_API_KEY`` is not set so callers can
    degrade gracefully instead of failing the whole run.
    """
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
        content = response.message.content
        if isinstance(content, list) and content:
            first = content[0]
            text = getattr(first, "text", None)
            if text is None and isinstance(first, dict):
                text = first.get("text")
            if text is None:
                return None
            return str(text).strip()
        if isinstance(content, str):
            return content.strip()
        text = getattr(content, "text", None)
        return str(text).strip() if text else None
    except Exception as error:
        logger.warning("cohere %s call failed: %s", model, error)
        return None


_WHITESPACE_RE = re.compile(r"\s+")


def _clean(s: str) -> str:
    return _WHITESPACE_RE.sub(" ", s).strip()


@lru_cache(maxsize=20000)
def ar_to_en(name: str) -> str:
    """Translate an Arabic drug name to its English equivalent.

    Returns the input unchanged when translation is unavailable so
    the matcher can still run.
    """
    if not name:
        return name
    cleaned = _clean(name)
    primary = _call_cohere(PRIMARY_MODEL, cleaned)
    if primary:
        return primary
    fallback = _call_cohere(FALLBACK_MODEL, cleaned)
    if fallback:
        return fallback
    return cleaned
