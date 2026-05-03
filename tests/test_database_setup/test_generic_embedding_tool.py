import os
import numpy as np
import pytest

from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore
from tooluniverse.database_setup.embedder import Embedder
from tooluniverse.database_setup.generic_embedding_search_tool import EmbeddingCollectionSearchTool

def _require_online_env_or_fail():
    prov = os.getenv("EMBED_PROVIDER")
    assert prov in {"azure", "openai", "huggingface", "local"}, "Set EMBED_PROVIDER"
    if prov == "azure":
        missing = [k for k in ["AZURE_OPENAI_API_KEY","AZURE_OPENAI_ENDPOINT","OPENAI_API_VERSION"] if not os.getenv(k)]
        assert not missing, f"Missing Azure vars: {missing}"
        model = os.getenv("EMBED_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        assert model, "Set EMBED_MODEL or AZURE_OPENAI_DEPLOYMENT"
        return prov, model
    if prov == "openai":
        assert os.getenv("OPENAI_API_KEY"), "Missing OPENAI_API_KEY"
        model = os.getenv("EMBED_MODEL")
        assert model, "Set EMBED_MODEL"
        return prov, model
    if prov == "huggingface":
        assert os.getenv("HF_TOKEN"), "Missing HF_TOKEN"
        model = os.getenv("EMBED_MODEL")
        assert model, "Set EMBED_MODEL"
        return prov, model
    # local
    model = os.getenv("EMBED_MODEL")
    assert model, "Set EMBED_MODEL for local"
    return prov, model

@pytest.mark.api
@pytest.mark.skip(reason="Requires EMBED_PROVIDER environment variable")
def test_generic_embedding_tool_hybrid_real(tmp_path):
    provider, model = _require_online_env_or_fail()

    db_path = str(tmp_path / "emb.db")
    store = SQLiteStore(db_path)
    vs = VectorStore(db_path)

    store.upsert_collection("toy", description="Toy", embedding_model=model, embedding_dimensions=1536)
    docs = [
        ("d1", "Mitochondria is the powerhouse of the cell.", {"topic": "bio"}, "h1"),
        ("d2", "Insulin is a hormone regulating glucose.", {"topic": "med"}, "h2"),
    ]
    store.insert_docs("toy", docs)

    emb = Embedder(provider=provider, model=model)
    rows = store.fetch_docs("toy", limit=100)
    texts = [r["text"] for r in rows]
    doc_ids = [r["id"] for r in rows]

    doc_vecs = emb.embed(texts).astype("float32")
    dim = int(doc_vecs.shape[1])
    store.upsert_collection("toy", embedding_model=model, embedding_dimensions=dim)

    doc_vecs = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-12)
    vs.add_embeddings("toy", doc_ids, doc_vecs, dim=dim)

    tool = EmbeddingCollectionSearchTool(tool_config={"fields": {"collection": "toy", "db_path": db_path}})
    out = tool.run({"query": "glucose", "method": "hybrid", "top_k": 5, "alpha": 0.5})

    assert isinstance(out, list) and len(out) >= 1
    assert "snippet" in out[0]
    texts_out = [r.get("text","").lower() for r in out]
    assert any("glucose" in t for t in texts_out)
