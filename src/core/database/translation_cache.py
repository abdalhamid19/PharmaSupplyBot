"""Persistent translation cache for the bilingual matcher.

Stores Arabic→English drug-name translations in the same SQLite
database used by the order-runs analytics. The cache outlives a
single Python process so the second run of an order against a
catalog that has already been translated costs zero Cohere calls.

Schema (migration-safe):

* ``translation_cache`` is created by :func:`bootstrap` so callers
  don't need to manage a separate database.
* The primary key is the normalized Arabic text. We store both the
  raw input (for display) and the normalized form (for lookup).
* A ``model`` column records which Cohere model produced the
  translation, so we can invalidate entries when we switch models.
* A ``hits`` counter tracks how many times an entry was reused,
  which makes the cache worth tuning later.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

logger = logging.getLogger(__name__)


DEFAULT_DB_PATH = Path("state/order_runs.db")


CREATE_TABLE = """
create table if not exists translation_cache (
    normalized_ar  text primary key,
    raw_ar         text not null,
    en_text        text not null,
    model          text not null,
    hits           integer not null default 0,
    created_at     text not null default current_timestamp
)
"""

CREATE_INDEX_HITS = """
create index if not exists ix_translation_cache_hits
on translation_cache (hits desc)
"""

ALL_DDL = (CREATE_TABLE, CREATE_INDEX_HITS)


def normalize_key(text: str) -> str:
    """Normalize Arabic text to a stable lookup key.

    Strips whitespace, tatweel, harakat and collapses alef variants.
    Whitespace tokens are deduped and sorted so re-ordered inputs
    share the same key.
    """
    if not text:
        return ""
    try:
        import pyarabic.araby as ar
    except ImportError:
        return " ".join(text.split())
    s = ar.strip_tashkeel(text)
    s = ar.strip_tatweel(s)
    s = ar.normalize_ligature(s)
    s = ar.normalize_hamza(s, method="tasheel")
    tokens = s.split()
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return " ".join(ordered)


_lock = threading.Lock()


@contextmanager
def _connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def bootstrap(db_path: Path | None = None) -> Path:
    """Create the translation_cache table on first call."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as conn:
        for ddl in ALL_DDL:
            conn.execute(ddl)
    return path


def _ensure_schema(db_path: Path | None = None) -> Path:
    path = db_path or DEFAULT_DB_PATH
    with _connect(path) as conn:
        c = conn.execute(
            "select 1 from sqlite_master where type='table' and name='translation_cache'"
        )
        if c.fetchone() is None:
            for ddl in ALL_DDL:
                conn.execute(ddl)
    return path


class TranslationCache:
    """Thread-safe wrapper around the translation_cache table."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = _ensure_schema(db_path)

    def get_many(self, arabic_texts: Iterable[str]) -> dict[str, str]:
        """Return ``{ar_key: en_text}`` for every key already in the cache.

        Missing keys are simply absent from the result; the caller is
        expected to translate the remainder.
        """
        keys = [normalize_key(t) for t in arabic_texts]
        keys = [k for k in keys if k]
        if not keys:
            return {}
        with self._connect() as conn:
            placeholders = ",".join("?" for _ in keys)
            rows = conn.execute(
                f"select normalized_ar, en_text from translation_cache where normalized_ar in ({placeholders})",
                keys,
            ).fetchall()
        result = {row["normalized_ar"]: row["en_text"] for row in rows}
        if result:
            with self._connect() as conn:
                conn.executemany(
                    "update translation_cache set hits = hits + 1 where normalized_ar = ?",
                    [(k,) for k in result],
                )
        return result

    def get_many_by_raw(self, raw_arabic_texts: Iterable[str]) -> dict[str, str]:
        """Like :meth:`get_many` but matches against ``raw_ar`` (the original
        text as written, before any normalization) and returns the
        ``raw_ar → en_text`` mapping.

        Use this when the caller has the exact string the Excel cell
        contained (including double-spaces) and the lookup key is the
        raw cell content rather than the normalized form.
        """
        raws = [str(t) for t in raw_arabic_texts if t]
        if not raws:
            return {}
        with self._connect() as conn:
            placeholders = ",".join("?" for _ in raws)
            rows = conn.execute(
                f"select raw_ar, en_text from translation_cache where raw_ar in ({placeholders})",
                raws,
            ).fetchall()
        result = {row["raw_ar"]: row["en_text"] for row in rows}
        if result:
            with self._connect() as conn:
                conn.executemany(
                    "update translation_cache set hits = hits + 1 where raw_ar = ?",
                    [(k,) for k in result],
                )
        return result

    def put_many(
        self,
        entries: dict[str, str],
        model: str,
    ) -> int:
        """Upsert ``{raw_ar: en_text}`` into the cache.

        Returns the number of rows written (new + replaced).
        """
        if not entries:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                insert into translation_cache (normalized_ar, raw_ar, en_text, model)
                values (?, ?, ?, ?)
                on conflict(normalized_ar) do update set
                    en_text = excluded.en_text,
                    model = excluded.model,
                    raw_ar = excluded.raw_ar
                """,
                [(normalize_key(ar), ar, en, model) for ar, en in entries.items()],
            )
        return len(entries)

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            row = conn.execute(
                "select count(*) as n, coalesce(sum(hits), 0) as total_hits from translation_cache"
            ).fetchone()
        return {"entries": row["n"], "total_hits": row["total_hits"]}

    def _connect(self) -> sqlite3.Connection:
        with _lock:
            conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn


__all__ = [
    "TranslationCache",
    "bootstrap",
    "normalize_key",
    "ALL_DDL",
    "DEFAULT_DB_PATH",
]
