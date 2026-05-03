"""
SQLiteStore: lightweight content store with FTS5 search and vector metadata.

This module implements the relational half of the datastore:
- Tables:
  - collections(name TEXT PRIMARY KEY, description TEXT, embedding_model TEXT, embedding_dimensions INT)
  - docs(id INTEGER PRIMARY KEY, collection TEXT, doc_key TEXT, text TEXT, text_norm TEXT, metadata JSON, text_hash TEXT)
  - vectors(doc_id INT, collection TEXT, have_vector INT DEFAULT 0)
- Virtual table:
  - docs_fts(text_norm) -> FTS5 mirror of docs.text_norm for keyword search

Key invariants
--------------
1) (collection, doc_key) is unique: a document identity must be stable across rebuilds.
2) (collection, text_hash) is unique WHEN text_hash IS NOT NULL: prevents duplicate content in the same collection.
3) docs_fts stays in sync through triggers on insert/update/delete.
4) embedding_dimensions in `collections` must match the dimensionality of vectors added for that collection.

Typical flow
------------
- upsert_collection(...) once
- insert_docs(...): accepts (doc_key, text, metadata, [text_hash]) tuples (hash auto-computed if missing)
- fetch_docs(...): returns rows for embedding/indexing or inspection
- search_keyword(...): keyword search via FTS5 (accent/case tolerant)
- A separate VectorStore persists FAISS vectors; SearchEngine orchestrates hybrid search.

See also
--------
- vector_store.py  : FAISS index management
- search.py        : keyword/embedding/hybrid orchestration
- pipeline.py      : high-level "build then search" helpers
"""

import sqlite3
import json
import time
import unicodedata
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding_model TEXT,
    embedding_dimensions INTEGER,
    index_type TEXT
);

CREATE TABLE IF NOT EXISTS docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection TEXT NOT NULL,
    doc_key TEXT NOT NULL,
    text TEXT NOT NULL,
    text_norm TEXT,
    metadata_json TEXT,
    text_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(collection, doc_key)
);

CREATE TABLE IF NOT EXISTS vectors (
    doc_id INTEGER UNIQUE,
    collection TEXT NOT NULL,
    faiss_idx INTEGER,
    FOREIGN KEY(doc_id) REFERENCES docs(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    text,
    text_norm,
    content='docs',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
  INSERT INTO docs_fts(rowid, text, text_norm)
  VALUES (new.id, new.text, new.text_norm);
END;

CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, text, text_norm)
  VALUES('delete', old.id, old.text, old.text_norm);
END;

CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
  INSERT INTO docs_fts(docs_fts, rowid, text, text_norm)
  VALUES('delete', old.id, old.text, old.text_norm);
  INSERT INTO docs_fts(rowid, text, text_norm)
  VALUES (new.id, new.text, new.text_norm);
END;
"""


def normalize_text(val: str) -> str:
    """Lowercase, strip accents (NFKD), and collapse whitespace."""
    if not val:
        return ""
    val = val.lower().strip()
    val = unicodedata.normalize("NFKD", val)
    val = "".join(c for c in val if not unicodedata.combining(c))
    return " ".join(val.split())


def safe_for_fts(query: str) -> str:
    """Sanitize a free-text query for FTS5 MATCH by removing quotes and breaking '-', ',', ':'."""
    if not query:
        return ""
    q = query.replace("-", " ").replace(",", " ").replace(":", " ")
    q = q.strip('"').strip("'")
    return q.strip()


def _ensure_fts5(conn):
    """
    Ensure that the current sqlite3 build supports FTS5.
    Raise a user-friendly error if not.
    """
    try:
        conn.execute("CREATE VIRTUAL TABLE temp._fts5_test USING fts5 (x);")
        conn.execute("DROP TABLE temp._fts5_test;")
    except Exception:
        raise RuntimeError(
            "\nERROR: SQLite in your Python environment is missing FTS5 support.\n"
            "FTS5 is required for keyword/hybrid search in ToolUniverse.\n\n"
            "To fix this:\n"
            "  Option 1 (Recommended): Use Homebrew Python *and* Homebrew SQLite:\n"
            "      brew install sqlite\n"
            "      brew install python@3.12\n"
            "      opt/homebrew/bin/python3.12 -m venv .venv\n"
            "      source .venv/bin/activate\n"
            "      pip install -e .\n\n"
            "  Option 2: Use pysqlite3-binary:\n"
            "      pip install pysqlite3-binary\n\n"
            "  Option 3: Build your own EUHealth datastore locally with tu-datastore,\n"
            "            which ships with FTS5 enabled.\n"
        )


class SQLiteStore:
    """Lightweight SQLite store with FTS5 mirror and vector bookkeeping.

    Creates schema/triggers on first use and exposes helpers to manage
    collections, documents, and FTS5 keyword search.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        _ensure_fts5(self.conn)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.executescript(SCHEMA)
        # Try to create the dedupe index, but ignore errors if existing data violates it
        try:
            self.conn.execute(
                """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_docs_collection_text_hash
            ON docs(collection, text_hash) WHERE text_hash IS NOT NULL
            """
            )
        except sqlite3.IntegrityError:
            # Existing DB may contain duplicates; keep working, just skip enforcing
            pass
        self.conn.commit()

    # ---- Collections ----
    def upsert_collection(
        self,
        name: str,
        description: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_dimensions: Optional[int] = None,
        index_type: str = "IndexFlatIP",
    ):
        """Create or update a row in `collections` with optional embedding metadata.

        Keeps `updated_at` fresh and sets/updates description, embedding_model,
        embedding_dimensions, and index_type when provided.
        """

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            """
            INSERT INTO collections (name, description, embedding_model, embedding_dimensions, index_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                description=excluded.description,
                embedding_model=excluded.embedding_model,
                embedding_dimensions=excluded.embedding_dimensions,
                index_type=excluded.index_type,
                updated_at=excluded.updated_at
            """,
            (
                name,
                description,
                embedding_model,
                embedding_dimensions,
                index_type,
                now,
                now,
            ),
        )
        self.conn.commit()

    # ---- Docs ----
    def insert_docs(
        self,
        collection: str,
        docs: List[Tuple[str, str, Dict[str, Any], Optional[str]]],
    ):
        """Insert a batch of documents with de-dup by (collection, doc_key) and (collection, text_hash).

        - Computes `text_norm` using normalize_text.
        - Normalizes string/list metadata values for the *_norm fields used by FTS.
        - Maintains docs_fts via triggers.
        """

        rows = []
        for doc in docs:
            if len(doc) == 3:
                key, text, meta = doc
                text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            elif len(doc) == 4:
                key, text, meta, text_hash = doc
                if text_hash is None:
                    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            else:
                raise ValueError(f"insert_docs expected 3 or 4 values, got {len(doc)}")

            norm_meta = {}
            for k, v in (meta or {}).items():
                if isinstance(v, str):
                    norm_meta[k] = normalize_text(v)
                elif isinstance(v, list):
                    norm_meta[k] = [
                        normalize_text(x) if isinstance(x, str) else x for x in v
                    ]
                else:
                    norm_meta[k] = v
            text_norm = normalize_text(text)

            rows.append(
                (collection, key, text, text_norm, json.dumps(norm_meta), text_hash)
            )

        self.conn.executemany(
            """
            INSERT OR IGNORE INTO docs (collection, doc_key, text, text_norm, metadata_json, text_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def fetch_docs(
        self, collection: str, doc_keys: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch documents by collection (optionally filtered by doc_key list).

        Returns a list of dicts: {id, doc_key, text, metadata}.
        Order is unspecified.
        """

        q = "SELECT id, doc_key, text, metadata_json FROM docs WHERE collection=?"
        args: List[Any] = [collection]
        if doc_keys:
            q += " AND doc_key IN (%s)" % ",".join("?" for _ in doc_keys)
            args.extend(doc_keys)
        q += " LIMIT ?"
        args.append(limit)
        cur = self.conn.execute(q, args)
        rows = cur.fetchall()
        results = []
        for doc_id, doc_key, text, meta_json in rows:
            meta = json.loads(meta_json) if meta_json else {}
            results.append(
                {"id": doc_id, "doc_key": doc_key, "text": text, "metadata": meta}
            )
        return results

    def fetch_random_docs(self, collection: str, n: int = 5):
        """Return `n` random docs from a collection for sampling/demo."""
        cur = self.conn.execute(
            "SELECT id, doc_key, text, metadata_json FROM docs WHERE collection=? ORDER BY RANDOM() LIMIT ?",
            (collection, n),
        )
        rows = cur.fetchall()
        results = []
        for doc_id, doc_key, text, meta_json in rows:
            meta = json.loads(meta_json) if meta_json else {}
            results.append(
                {"id": doc_id, "doc_key": doc_key, "text": text, "metadata": meta}
            )
        return results

    def search_keyword(
        self, collection: str, query: str, limit: int = 5, use_norm: bool = True
    ):
        """FTS5 keyword search on `text_norm` (or `text` if use_norm=False).

        Parameters
        ----------
        query : str
            Free-text query; sanitized for FTS via safe_for_fts().
        limit : int
            Max rows to return.

        Returns
        -------
        List[dict]
            Each with {id, doc_key, text, metadata}.
        """

        safe_query = safe_for_fts(query)
        if not safe_query:
            return []
        field = "text_norm" if use_norm else "text"
        fts_query = f'{field}:"{safe_query}"'

        with self.conn:
            cur = self.conn.execute(
                """
                SELECT d.id, d.doc_key, d.text, d.metadata_json
                FROM docs_fts
                JOIN docs d ON d.id = docs_fts.rowid
                WHERE docs_fts MATCH ?
                LIMIT ?
                """,
                (fts_query, limit),
            )
            rows = cur.fetchall()

        results = []
        for doc_id, doc_key, text, meta_json in rows:
            meta = json.loads(meta_json) if meta_json else {}
            results.append(
                {"id": doc_id, "doc_key": doc_key, "text": text, "metadata": meta}
            )
        return results

    def fetch_docs_by_ids(
        self, collection: str, doc_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Fetch documents by SQLite row ids limited to those mapped in `vectors` for the collection."""

        if not doc_ids:
            return []
        placeholders = ",".join("?" for _ in doc_ids)
        q = f"""
            SELECT d.id, d.doc_key, d.text, d.metadata_json
            FROM docs d
            JOIN vectors v ON d.id = v.doc_id
            WHERE v.collection=? AND d.id IN ({placeholders})
        """
        args = [collection] + doc_ids
        cur = self.conn.execute(q, args)
        rows = cur.fetchall()
        results = []
        for doc_id, doc_key, text, meta_json in rows:
            meta = json.loads(meta_json) if meta_json else {}
            results.append(
                {"id": doc_id, "doc_key": doc_key, "text": text, "metadata": meta}
            )
        return results

    def close(self):
        """Close the underlying SQLite connection."""
        self.conn.close()
