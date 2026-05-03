import os
import numpy as np
import pytest

from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore
from tooluniverse.database_setup.embedder import Embedder
from tooluniverse.database_setup.search import SearchEngine

def _resolve_provider_model_or_skip():
    prov = os.getenv("EMBED_PROVIDER")
    model = os.getenv("EMBED_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not prov or not model:
        pytest.skip("Set EMBED_PROVIDER and EMBED_MODEL/AZURE_OPENAI_DEPLOYMENT")
    return prov, model

@pytest.mark.api
def test_search_engine_embedding(tmp_path):
    provider, model = _resolve_provider_model_or_skip()
    db = str(tmp_path / "demo.db")

    store = SQLiteStore(db)
    vs = VectorStore(db)

    store.upsert_collection("demo", embedding_model=model, embedding_dimensions=1536)
    docs = [
        ("uuid-1", "Hypertension treatment guidelines for adults", {"topic": "bp"}, "h1"),
        ("uuid-2", "Diabetes prevention programs in Germany", {"topic": "dm"}, "h2"),
    ]
    store.insert_docs("demo", docs)

    rows = store.fetch_docs("demo")
    ids = [r["id"] for r in rows]
    texts = [r["text"] for r in rows]
    emb = Embedder(provider=provider, model=model)
    vecs = emb.embed(texts).astype("float32")
    dim = int(vecs.shape[1])
    store.upsert_collection("demo", embedding_model=model, embedding_dimensions=dim)
    # reset FAISS so it only has these vectors
    vs.load_index("demo", dim, reset=True)
    vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    vs.add_embeddings("demo", ids, vecs, dim=dim)
    engine = SearchEngine(db_path=db)
    res = engine.embedding_search("demo", "hypertension", top_k=5)

    assert isinstance(res, list) and len(res) >= 1

@pytest.mark.api
def test_search_engine_hybrid(tmp_path):
    provider, model = _resolve_provider_model_or_skip()
    db = str(tmp_path / "demo2.db")

    store = SQLiteStore(db)
    vs = VectorStore(db)
    store.upsert_collection("demo", embedding_model=model, embedding_dimensions=1536)
    store.insert_docs("demo", [
        ("uuid-1", "Hypertension treatment guidelines for adults", {"topic":"bp"}, "h1"),
        ("uuid-2", "Diabetes prevention programs in Germany", {"topic":"dm"}, "h2"),
    ])
    rows = store.fetch_docs("demo")
    ids = [r["id"] for r in rows]
    texts = [r["text"] for r in rows]
    emb = Embedder(provider=provider, model=model)
    vecs = emb.embed(texts).astype("float32")
    dim = int(vecs.shape[1])
    store.upsert_collection("demo", embedding_model=model, embedding_dimensions=dim)
    vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    vs.add_embeddings("demo", ids, vecs, dim=dim)

    engine = SearchEngine(db_path=db)
    res = engine.hybrid_search("demo", "hypertension", top_k=5, alpha=0.7)
    assert isinstance(res, list) and len(res) >= 1
