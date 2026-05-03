import os
import numpy as np
import pytest
from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore
from tooluniverse.database_setup.search import SearchEngine

@pytest.fixture()
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")

@pytest.fixture()
def demo_docs():
    return [
        ("uuid-1", "Hypertension treatment guidelines for adults", {"topic": "bp"}, "h1"),
        ("uuid-2", "Diabetes prevention programs in Germany", {"topic": "dm"}, "h2"),
    ]

@pytest.fixture()
def store(tmp_db, demo_docs):
    st = SQLiteStore(tmp_db)
    st.upsert_collection("demo", description="Demo", embedding_model="test-model", embedding_dimensions=4)
    st.insert_docs("demo", demo_docs)
    yield st
    st.close()

@pytest.fixture()
def vector(tmp_db):
    return VectorStore(tmp_db)

@pytest.fixture()
def doc_ids(store):
    rows = store.fetch_docs("demo")
    return [r["id"] for r in rows]

@pytest.fixture()
def engine(tmp_db):
    return SearchEngine(db_path=tmp_db)

@pytest.fixture()
def add_fake_embeddings(store, vector, doc_ids):
    # two deterministic, L2-normalized 4D vectors
    vecs = np.array([
        [0.1, 0.2, 0.3, 0.4],
        [0.2, 0.1, 0.4, 0.3],
    ], dtype="float32")
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    vector.add_embeddings("demo", doc_ids, vecs)
    return vecs

@pytest.fixture()
def monkeypatch_search_embed(engine):
    # Monkeypatch SearchEngine.embedder.embed to a fixed vector
    def _fake(texts):
        v = np.array([[0.1, 0.2, 0.3, 0.4]], dtype="float32")
        v = v / np.linalg.norm(v, axis=1, keepdims=True)
        return v
    engine.embedder.embed = _fake
    return engine
