"""
SearchEngine: unified keyword / embedding / hybrid search over a SQLite+FAISS datastore.

Composes:
- SQLiteStore.search_keyword(...)
- Embedder for query-time vectors
- VectorStore.search_embeddings(...)
- A simple hybrid combiner to mix keyword and embedding scores

Scoring
-------
- Keyword scores are alway 1.0.
- Embedding scores are FAISS IP (assume vectors are L2-normalized upstream).
- Hybrid: score = alpha * embed_score + (1 - alpha) * keyword_score  (alpha in [0,1]).

Return shape
------------
Each API returns a list of dicts:
{ "doc_id", "doc_key", "text", "metadata", "score" }

See also
--------
- pipeline.py for high-level build & search helpers
- cli.py for command-line usage
"""

from typing import List, Dict, Any, Optional

from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore
from tooluniverse.database_setup.embedder import Embedder
from tooluniverse.database_setup.provider_resolver import (
    resolve_provider,
    resolve_model,
)

import numpy as np


class SearchEngine:
    """
    Unified keyword + embedding + hybrid search for a given DB path.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file that also anchors <collection>.faiss files.
    provider : Optional[str]
        Default embedder provider. May be overridden per-call.
    model : Optional[str]
        Default embedding model. May be overridden per-call.

    Use
    ---
    Provides consistent records ``{doc_id, doc_key, text, metadata, score}``.
    Keyword results get a fixed ``score=1.0``; hybrid combines embedding/keyword scores as ``alpha*emb + (1-alpha)*kw``.

    Notes
    -----
    - If a collection's `embedding_model` is "precomputed", you MUST pass (provider, model)
      when calling `embedding_search` or `hybrid_search`.
    """

    def __init__(self, db_path: str = "embeddings.db"):
        self.sqlite = SQLiteStore(db_path)
        self.vectors = VectorStore(db_path)
        # Lazy embedder, only created if/when user actually does embedding.
        self.embedder: Optional[Embedder] = None

    def _get_default_embedder(self) -> Embedder:
        """Return a lazily constructed default Embedder.

        This avoids importing sentence_transformers (for provider=='local')
        unless we *actually* perform an embedding or hybrid search.
        """
        if self.embedder is not None:
            return self.embedder

        prov = resolve_provider()
        mdl = resolve_model(prov)
        self.embedder = Embedder(provider=prov, model=mdl)
        return self.embedder

    def _get_collection_meta(self, collection: str):
        cur = self.sqlite.conn.execute(
            "SELECT embedding_model, embedding_dimensions FROM collections WHERE name=? LIMIT 1",
            (collection,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)

    # ---- Keyword search ----
    def keyword_search(
        self, collection: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """FTS5 keyword search (normalized text). Returns fixed score=1.0 hits."""
        rows = self.sqlite.search_keyword(collection, query, limit=top_k)
        return [
            {
                "doc_id": r["id"],
                "doc_key": r["doc_key"],
                "text": r["text"],
                "metadata": r["metadata"],
                "score": 1.0,  # fixed score (FTS5 doesn’t give ranking)
            }
            for r in rows
        ]

    # ---- Embedding search ----
    def embedding_search(
        self, collection: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Vector search using FAISS (IndexFlatIP with L2-normalized vectors)."""
        col_model, col_dim = self._get_collection_meta(collection)
        prov = resolve_provider()
        # if the collection records a model (and it's not the placeholder), prefer it
        model = (
            col_model
            if (col_model and col_model != "precomputed")
            else resolve_model(prov)
        )

        # instantiate a per-call embedder if needed to match the collection
        base_emb = self._get_default_embedder()
        emb = base_emb
        if (getattr(base_emb, "model", None) != model) or (
            col_dim and self.vectors.dimensions.get(collection) != col_dim
        ):
            # collection was built with a different model – use a fresh embedder
            emb = Embedder(provider=prov, model=model)

        q = emb.embed([query])[0]
        q = q / (np.linalg.norm(q, keepdims=True) + 1e-12)
        self.vectors.load_index(collection, col_dim or len(q))

        if col_dim and col_dim != len(q):
            raise ValueError(
                f"Embedding dimension mismatch: index={col_dim}, query={len(q)} (model={model})"
            )

        results = self.vectors.search_embeddings(collection, q, top_k=top_k)
        doc_ids = [doc_id for doc_id, _ in results]
        docs = self.sqlite.fetch_docs_by_ids(collection, doc_ids)
        doc_map = {d["id"]: d for d in docs}

        out = []
        for doc_id, score in results:
            d = doc_map.get(doc_id)
            if d:
                out.append(
                    {
                        "doc_id": d["id"],
                        "doc_key": d["doc_key"],
                        "text": d["text"],
                        "metadata": d["metadata"],
                        "score": float(score),
                    }
                )
        return out

    # ---- Hybrid search ---- (embedding + keyword)
    def hybrid_search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Blend keyword and embedding results with score = alpha*emb + (1-alpha)*kw."""
        kws = self.keyword_search(collection, query, top_k=top_k * 2)
        embs = self.embedding_search(collection, query, top_k=top_k * 2)

        kw_scores = {r["doc_id"]: r for r in kws}
        emb_scores = {r["doc_id"]: r for r in embs}
        all_ids = set(kw_scores) | set(emb_scores)

        combined = []
        for doc_id in all_ids:
            kw = kw_scores.get(doc_id, {"score": 0.0})
            emb = emb_scores.get(doc_id, {"score": 0.0})
            kw_score = kw["score"]
            emb_score = emb["score"]
            score = alpha * emb_score + (1 - alpha) * kw_score
            doc = emb if doc_id in emb_scores else kw
            combined.append(
                {**doc, "kw_score": kw_score, "emb_score": emb_score, "score": score}
            )

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:top_k]

    # ---- Collection + Doc Access ----
    def list_collections(self) -> List[str]:
        """Return the list of collection names registered in the SQLite `collections` table."""
        cur = self.sqlite.conn.execute("SELECT name FROM collections")
        return [r[0] for r in cur.fetchall()]

    def fetch_docs(self, collection: str, doc_keys: List[str] = None, limit: int = 10):
        """Fetch raw docs by doc_key using SQLiteStore.fetch_docs (for inspection or tooling)."""
        return self.sqlite.fetch_docs(collection, doc_keys=doc_keys, limit=limit)

    def fetch_random_docs(self, collection: str, n: int = 5):
        """Return `n` random documents from a collection (for sampling/demo)."""
        return self.sqlite.fetch_random_docs(collection, n=n)

    # ---- Unified search ----
    def search_collection(
        self,
        collection: str,
        query: str,
        method: str = "hybrid",
        top_k: int = 5,
        alpha: float = 0.5,
    ):
        """Dispatch to keyword/embedding/hybrid search for a single collection."""
        if method == "keyword":
            return self.keyword_search(collection, query, top_k=top_k)
        elif method == "embedding":
            return self.embedding_search(collection, query, top_k=top_k)
        elif method == "hybrid":
            return self.hybrid_search(collection, query, top_k=top_k, alpha=alpha)
        else:
            raise ValueError(f"Unknown method: {method}")

    def multi_collection_search(
        self, query: str, method: str = "hybrid", top_k: int = 5, alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Run the same query across all collections and return top-k by score.

        Notes
        -----
        - Attaches a 'collection' field to each hit.
        - Silently warns and skips collections that fail to search.
        """
        collections = self.list_collections()
        all_results = []
        for coll in collections:
            try:
                results = self.search_collection(
                    coll, query, method=method, top_k=top_k, alpha=alpha
                )
                for r in results:
                    r["collection"] = coll
                all_results.extend(results)
            except Exception as e:
                print(f"[WARN] Failed on {coll}: {e}")
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]
