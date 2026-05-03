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
def test_end_to_end_local(tmp_path):
    provider, model = _resolve_provider_model_or_skip()

    db_path = str(tmp_path / "integration.db")
    store = SQLiteStore(db_path)
    vs = VectorStore(db_path)

    store.upsert_collection("integration_demo", description="Integration demo", embedding_model=model, embedding_dimensions=1536)
    docs = [
    ("uuid-10", "Hypertension treatment guidelines for adults", {"topic": "bp"}, "h10"),
    ("uuid-11", "Diabetes prevention programs in Germany", {"topic": "dm"}, "h11"),
    ("uuid-12", "hypertension", {"topic": "bp"}, "h12"), 
    ]
    store.insert_docs("integration_demo", docs)

    rows = store.fetch_docs("integration_demo")
    ids = [r["id"] for r in rows]
    texts = [r["text"] for r in rows]

    emb = Embedder(provider=provider, model=model)
    vecs = emb.embed(texts).astype("float32")
    dim = int(vecs.shape[1])
    store.upsert_collection("integration_demo", embedding_model=model, embedding_dimensions=dim)
    vs.load_index("integration_demo", dim, reset=True)
    vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    vs.add_embeddings("integration_demo", ids, vecs, dim=dim)
    se = SearchEngine(db_path=db_path)

    k = se.keyword_search("integration_demo", "hypertension")
    e = se.embedding_search("integration_demo", "hypertension")
    h = se.hybrid_search("integration_demo", "hypertension", alpha=0.7)

    assert len(k) >= 1
    assert len(e) >= 1
    assert len(h) >= 1
