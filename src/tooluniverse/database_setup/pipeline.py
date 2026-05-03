"""
High-level helpers for building and querying collections.

Exposes
-------
build_collection(db_path, collection, docs, embed_provider, embed_model, overwrite=False)
    Create or extend a collection, insert documents with de-dup, embed texts, and persist a FAISS index.
search(db_path, collection, query, method="hybrid", top_k=10, alpha=0.5, embed_provider=None, embed_model=None)
    Keyword/embedding/hybrid search over an existing collection.

Notes
-----
- Input docs are (doc_key, text, metadata, [text_hash]).
- If a collection records embedding_model="precomputed", you must provide an embed
  provider/model at query time for embedding/hybrid searches.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import sqlite3

from .sqlite_store import SQLiteStore
from .vector_store import VectorStore
from .embedder import Embedder
from tooluniverse.database_setup.provider_resolver import (
    resolve_provider,
    resolve_model,
)
from tooluniverse.database_setup.embed_utils import get_model_dim


def _l2norm(x: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalization with an epsilon guard."""
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-12)


def _get_collection_meta(
    conn: sqlite3.Connection, name: str
) -> Tuple[Optional[str], Optional[int]]:
    """Return (embedding_model, embedding_dimensions) for a collection or (None, None)."""
    cur = conn.execute(
        "SELECT embedding_model, embedding_dimensions FROM collections WHERE name=? LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    return (row[0], row[1]) if row else (None, None)


def build_collection(
    db_path: str,
    collection: str,
    docs: List[tuple[str, str, Dict[str, Any], Optional[str]]],
    embed_provider: str,
    embed_model: str,
    overwrite: bool = False,
) -> None:
    """Create/extend a collection, embed docs, and populate FAISS.

    Inserts/merges documents (dedupe by (collection, doc_key) and by (collection, text_hash) when present),
    computes embeddings with the requested provider/model, L2-normalizes them,
    and appends to <collection>.faiss via VectorStore.

    Idempotency
    -----------
    Re-running is safe: existing (doc_key) are ignored; content duplicates (text_hash) are skipped.

    Side effects
    ------------
    - Records the true embedding model and dimension in the `collections` table.

    """
    print(f" Detecting embedding dimension for {embed_provider}:{embed_model} ...")
    try:
        embed_dim = get_model_dim(embed_provider, embed_model)
        print(f" Detected embedding dimension: {embed_dim}")
    except Exception as e:
        raise RuntimeError(f"Failed to detect embedding dimension: {e}")

    # os.makedirs(os.path.dirname(os.path.expanduser(db_path)), exist_ok=True)

    store = SQLiteStore(db_path)

    # Upsert collection metadata (safe to call repeatedly)

    store.upsert_collection(
        collection,
        description=f"Datastore for {collection}",
        embedding_model=embed_model,
        embedding_dimensions=embed_dim,
    )

    # Insert/merge docs (dedupe by (collection, doc_key); optional text_hash dedupe if index exists)
    store.insert_docs(collection, docs)

    # Fetch back to embed
    rows = store.fetch_docs(collection, limit=100000)
    if not rows:
        return

    texts = [r["text"] for r in rows]
    doc_ids = [r["id"] for r in rows]

    emb = Embedder(provider=embed_provider, model=embed_model)
    vecs = emb.embed(texts).astype("float32")
    vecs = _l2norm(vecs)
    print(f"Embedded {len(vecs)} docs with shape {vecs.shape}")

    vs = VectorStore(db_path)
    # Optionally reset existing FAISS index if overwrite=True
    vs.load_index(collection, dim=embed_dim, reset=overwrite)
    vs.add_embeddings(collection, doc_ids, vecs, dim=embed_dim)


# replace the beginning of search(...)
def search(
    db_path: str,
    collection: str,
    query: str,
    method: str = "hybrid",
    top_k: int = 10,
    alpha: float = 0.5,
    embed_provider: Optional[str] = None,
    embed_model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search a collection using keyword, embedding, or hybrid.

    Parameters
    ----------
    method : {"keyword", "embedding", "hybrid"}
        Search strategy. Hybrid mixes scores via `alpha * emb + (1 - alpha) * kw`.
    embed_provider, embed_model : Optional[str]
        Required if the collection’s embedding_model is "precomputed".

    Returns
    -------
    List[dict]
        Each hit: {doc_id, doc_key, text, metadata, score} (plus kw_score/emb_score in hybrid).

    Raises
    ------
    RuntimeError
        If embedding model information is insufficient for embedding/hybrid.
    """

    store = SQLiteStore(db_path)

    if method == "keyword":
        rows = store.search_keyword(collection, query, limit=top_k)
        return [
            {
                "doc_id": r["id"],
                "doc_key": r["doc_key"],
                "text": r["text"],
                "metadata": r["metadata"],
                "score": 1.0,
            }
            for r in rows
        ]

    model_from_db, dim_from_db = _get_collection_meta(store.conn, collection)
    # Resolve provider/model (env/creds if not supplied)
    resolved_provider = embed_provider or resolve_provider()
    if model_from_db is None or model_from_db == "precomputed":
        resolved_model = embed_model or resolve_model(resolved_provider)
    else:
        resolved_model = embed_model or model_from_db

    if resolved_model == "precomputed":
        raise RuntimeError(
            "This collection has precomputed embeddings. "
            "Supply embed_provider and embed_model for query embedding."
        )
    if dim_from_db is None:
        raise RuntimeError("Missing embedding_dimensions for this collection.")

    emb = Embedder(provider=resolved_provider, model=resolved_model)
    qvec = emb.embed([query]).astype("float32")
    qvec = _l2norm(qvec)[0]

    vs = VectorStore(db_path)
    vs.load_index(collection, dim_from_db)

    hits = vs.search_embeddings(
        collection, qvec, top_k=top_k * (2 if method == "hybrid" else 1)
    )

    doc_ids = [doc_id for doc_id, _ in hits]
    docs = store.fetch_docs_by_ids(collection, doc_ids)
    doc_map = {d["id"]: d for d in docs}

    emb_results = []
    for doc_id, score in hits:
        d = doc_map.get(doc_id)
        if d:
            emb_results.append(
                {
                    "doc_id": d["id"],
                    "doc_key": d["doc_key"],
                    "text": d["text"],
                    "metadata": d["metadata"],
                    "score": float(score),
                }
            )

    if method == "embedding":
        return emb_results[:top_k]

    # Hybrid combine
    kw_rows = store.search_keyword(collection, query, limit=top_k * 2)
    by_id: Dict[int, Dict[str, Any]] = {r["doc_id"]: r for r in emb_results}
    for r in kw_rows:
        if r["id"] in by_id:
            by_id[r["id"]]["kw_score"] = 1.0
        else:
            by_id[r["id"]] = {
                "doc_id": r["id"],
                "doc_key": r["doc_key"],
                "text": r["text"],
                "metadata": r["metadata"],
                "emb_score": 0.0,
                "kw_score": 1.0,
                "score": 0.0,
            }

    # Fill missing emb_score and compute final score
    out = []
    for v in by_id.values():
        emb_s = v.get("score", v.get("emb_score", 0.0))
        kw_s = v.get("kw_score", 0.0)
        v["score"] = alpha * float(emb_s) + (1 - alpha) * float(kw_s)
        out.append(v)

    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top_k]
