import numpy as np
from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore

def test_vector_store_add_and_search(tmp_path):
    db_path = str(tmp_path / "test.db")
    data_dir = tmp_path / "embeddings"   # isolate FAISS files
    store = SQLiteStore(db_path)
    vs = VectorStore(db_path, data_dir=str(data_dir))

    # Use a unique collection name for this test
    coll = "demo_vecstore"
    store.upsert_collection(coll, embedding_model="test-model", embedding_dimensions=4)
    store.insert_docs(coll, [("k1", "blood pressure doc", {"topic":"bp"}, "h1")])
    row = store.fetch_docs(coll)[0]
    doc_id = row["id"]

    vs.load_index(coll, dim=4)

    vec = np.array([[0.1, 0.2, 0.3, 0.4]], dtype="float32")
    vec = vec / np.linalg.norm(vec, axis=1, keepdims=True)
    vs.add_embeddings(coll, [doc_id], vec, dim=4)

    res = vs.search_embeddings(coll, vec[0], top_k=1)
    assert res and res[0][0] == doc_id
