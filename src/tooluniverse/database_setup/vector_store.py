"""
VectorStore: FAISS index management for per-collection embeddings.

This module encapsulates a single FAISS index per collection:
- Path convention: <user_cache_dir>/embeddings/<collection>.faiss (same base path as the SQLite file)
- Similarity: IndexFlatIP (inner product). With L2-normalized embeddings, IP ≈ cosine similarity.
- Mapping: you pass (doc_ids, vectors) in the same order; FAISS IDs are aligned to doc_ids internally.

Responsibilities
---------------
- Create/load a FAISS index with the correct dimensionality.
- Add new embeddings (append-only).
- Query nearest neighbors given a query vector.
- Persist the index to disk.

See also
--------
- embedder.py : turns text -> vector
- sqlite_store.py : stores docs and tracks which doc_ids have vectors
- search.py : orchestrates keyword/embedding/hybrid queries
"""

import faiss
import numpy as np
import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from tooluniverse.utils import get_user_cache_dir
import os


class VectorStore:
    """Manage FAISS indices per collection, persisted under the user cache dir (<user_cache_dir>/embeddings)."""

    def __init__(self, db_path: str, data_dir: str | None = None):
        self.db = sqlite3.connect(db_path)
        if data_dir is None:
            data_dir = os.path.join(get_user_cache_dir(), "embeddings")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # keep active indexes in memory
        self.indexes: Dict[str, faiss.Index] = {}
        self.dimensions: Dict[str, int] = {}

    def _get_index_path(self, collection: str) -> Path:
        return self.data_dir / f"{collection}.faiss"

    def load_index(self, collection: str, dim: int, reset: bool = False) -> faiss.Index:
        """
        Load or create a FAISS IndexFlatIP for the collection, asserting dimension consistency.
        If reset=True, always create a fresh index and overwrite any existing file.
        """
        path = self._get_index_path(collection)

        if reset or not path.exists():
            index = faiss.IndexFlatIP(dim)
            faiss.write_index(index, str(path))
        else:
            index = faiss.read_index(str(path))
            # in load_index(...)
            if index.d != dim:
                raise ValueError(
                    f"Existing FAISS index dim={index.d} does not match requested dim={dim} for collection '{collection}'"
                )
        self.indexes[collection] = index
        self.dimensions[collection] = dim
        return index

    # def save_index(self, collection: str):
    #   """Persist the in-memory FAISS index for `collection` to disk."""
    #   if collection not in self.indexes:
    #       raise ValueError(f"No index loaded for {collection}")
    #    faiss.write_index(
    #        self.indexes[collection], str(self._get_index_path(collection))
    #    )
    def save_index(self, collection: str):
        """Persist the in-memory FAISS index for `collection` to disk."""
        path = self._get_index_path(collection)
        print(f"[DEBUG] Writing FAISS index for '{collection}' to: {path}")
        if collection not in self.indexes:
            raise ValueError(f"No index loaded for {collection}")
        faiss.write_index(self.indexes[collection], str(path))

    def add_embeddings(
        self,
        collection: str,
        doc_ids: List[int],
        embeddings: np.ndarray,
        dim: Optional[int] = None,
    ):
        """Append embeddings to a collection index and record (doc_id ↔ faiss_idx) in SQLite.

        Expects embeddings to be float32 and L2-normalized (caller responsibility).
        """

        if dim is None:
            dim = embeddings.shape[1]

        index = self.indexes.get(collection) or self.load_index(collection, dim)

        if embeddings.shape[1] != self.dimensions[collection]:
            raise ValueError(
                f"Embedding dim mismatch: expected {self.dimensions[collection]}, got {embeddings.shape[1]}"
            )

        start_id = index.ntotal
        index.add(embeddings.astype("float32"))
        self.save_index(collection)

        # record mapping in SQLite
        cur = self.db.cursor()
        for i, doc_id in enumerate(doc_ids):
            faiss_idx = start_id + i
            cur.execute(
                """
                INSERT OR REPLACE INTO vectors (doc_id, collection, faiss_idx)
                VALUES (?, ?, ?)
                """,
                (doc_id, collection, faiss_idx),
            )
        self.db.commit()

    def search_embeddings(
        self,
        collection: str,
        query_vector: np.ndarray,
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """Nearest-neighbor search; returns [(doc_id, score), ...] in descending score order.

        Requires load_index() to have been called for the collection.
        """

        # auto-load index if present on disk
        if collection not in self.indexes:
            path = self._get_index_path(collection)
            if path.exists():
                index = faiss.read_index(str(path))
                self.indexes[collection] = index
                self.dimensions[collection] = index.d
            else:
                raise ValueError(
                    f"Index not loaded for {collection}. Call load_index() first."
                )

        index = self.indexes[collection]
        if query_vector.ndim == 1:
            query_vector = query_vector[np.newaxis, :]
        scores, ids = index.search(query_vector.astype("float32"), top_k)
        # Map faiss_idx back to doc_id
        cur = self.db.cursor()
        results: List[Tuple[int, float]] = []
        for faiss_idx, score in zip(ids[0], scores[0]):
            if faiss_idx == -1:
                continue
            row = cur.execute(
                "SELECT doc_id FROM vectors WHERE collection=? AND faiss_idx=?",
                (collection, int(faiss_idx)),
            ).fetchone()
            if row:
                results.append((row[0], float(score)))
        return results
