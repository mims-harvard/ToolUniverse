"""
SQLite-backed persistent cache for ToolUniverse.

The cache stores serialized tool results with TTL and version metadata.
Designed to be a drop-in persistent layer behind the in-memory cache.
"""

from __future__ import annotations

import os
import pickle
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional


@dataclass
class CacheEntry:
    key: str
    value: Any
    namespace: str
    version: str
    ttl: Optional[int]
    created_at: float
    last_accessed: float
    hit_count: int
    expires_at: Optional[float] = None  # Store expires_at from database


class PersistentCache:
    """SQLite-backed cache layer with TTL support."""

    def __init__(self, path: str, *, enable: bool = True):
        self.enabled = enable
        self.path = path
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None

        if self.enabled:
            self._init_storage()

    def _init_storage(self):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._conn = sqlite3.connect(
            self.path,
            timeout=30,
            check_same_thread=False,
            isolation_level=None,  # autocommit
        )
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._ensure_schema()
        self.cleanup_expired()

    def _ensure_schema(self):
        assert self._conn is not None
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                version TEXT,
                value BLOB NOT NULL,
                ttl INTEGER,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                expires_at REAL,
                hit_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_namespace ON cache_entries(namespace)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at)"
        )

    def _serialize(self, value: Any) -> bytes:
        return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, payload: bytes) -> Any:
        return pickle.loads(payload)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def cleanup_expired(self):
        if not self.enabled or not self._conn:
            return
        with self._lock:
            now = time.time()
            self._conn.execute(
                "DELETE FROM cache_entries WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            )

    def get(self, cache_key: str) -> Optional[CacheEntry]:
        if not self.enabled or not self._conn:
            return None
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT cache_key, namespace, version, value, ttl, created_at,
                       last_accessed, expires_at, hit_count
                FROM cache_entries WHERE cache_key = ?
                """,
                (cache_key,),
            )
            row = cur.fetchone()
            if not row:
                return None

            expires_at = row[7]
            if expires_at is not None and expires_at <= time.time():
                self._conn.execute(
                    "DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,)
                )
                return None

            entry = CacheEntry(
                key=row[0],
                namespace=row[1],
                version=row[2] or "",
                value=self._deserialize(row[3]),
                ttl=row[4],
                created_at=row[5],
                last_accessed=row[6],
                hit_count=row[8],
                expires_at=row[7],  # Store expires_at from database
            )

            self._conn.execute(
                """
                UPDATE cache_entries
                SET last_accessed = ?, hit_count = hit_count + 1
                WHERE cache_key = ?
                """,
                (time.time(), cache_key),
            )
            return entry

    def set(
        self,
        cache_key: str,
        value: Any,
        *,
        namespace: str,
        version: str,
        ttl: Optional[int],
        created_at: Optional[float] = None,
        expires_at: Optional[float] = None,
    ):
        if not self.enabled or not self._conn:
            return
        with self._lock:
            # Use provided timestamps if available, otherwise calculate them
            if created_at is None:
                created_at = time.time()
            if expires_at is None and ttl is not None:
                expires_at = created_at + ttl
            now = time.time()
            payload = self._serialize(value)
            self._conn.execute(
                """
                INSERT INTO cache_entries(cache_key, namespace, version, value, ttl,
                                          created_at, last_accessed, expires_at, hit_count)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(cache_key) DO UPDATE SET
                    namespace=excluded.namespace,
                    version=excluded.version,
                    value=excluded.value,
                    ttl=excluded.ttl,
                    created_at=excluded.created_at,
                    last_accessed=excluded.last_accessed,
                    expires_at=excluded.expires_at,
                    hit_count=excluded.hit_count
                """,
                (
                    cache_key,
                    namespace,
                    version,
                    payload,
                    ttl,
                    created_at,
                    now,
                    expires_at,
                ),
            )

    def delete(self, cache_key: str):
        if not self.enabled or not self._conn:
            return
        with self._lock:
            self._conn.execute(
                "DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,)
            )

    def clear(self, namespace: Optional[str] = None):
        if not self.enabled or not self._conn:
            return
        with self._lock:
            if namespace:
                self._conn.execute(
                    "DELETE FROM cache_entries WHERE namespace = ?", (namespace,)
                )
            else:
                self._conn.execute("DELETE FROM cache_entries")

    def iter_entries(self, namespace: Optional[str] = None) -> Iterator[CacheEntry]:
        if not self.enabled or not self._conn:
            return iter([])
        with self._lock:
            if namespace:
                cur = self._conn.execute(
                    """
                    SELECT cache_key, namespace, version, value, ttl,
                           created_at, last_accessed, expires_at, hit_count
                    FROM cache_entries WHERE namespace = ?
                    """,
                    (namespace,),
                )
            else:
                cur = self._conn.execute(
                    """
                    SELECT cache_key, namespace, version, value, ttl,
                           created_at, last_accessed, expires_at, hit_count
                    FROM cache_entries
                    """
                )
            rows = cur.fetchall()

        for row in rows:
            yield CacheEntry(
                key=row[0],
                namespace=row[1],
                version=row[2] or "",
                value=self._deserialize(row[3]),
                ttl=row[4],
                created_at=row[5],
                last_accessed=row[6],
                hit_count=row[8],
                expires_at=row[7],
            )

    def stats(self) -> Dict[str, Any]:
        if not self.enabled or not self._conn:
            return {"enabled": False}
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*), SUM(LENGTH(value)) FROM cache_entries"
            )
            count, total_bytes = cur.fetchone()
            return {
                "enabled": True,
                "entries": count or 0,
                "approx_bytes": total_bytes or 0,
                "path": self.path,
            }
