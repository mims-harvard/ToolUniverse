from tooluniverse.database_setup.sqlite_store import SQLiteStore

def test_sqlite_store_basic(tmp_db):
    store = SQLiteStore(tmp_db)
    store.upsert_collection("demo", description="Demo")
    docs = [
        ("k1", "Hypertension treatment guidelines", {"topic": "bp"}, "h1"),
        ("k2", "Diabetes prevention programs", {"topic": "dm"}, "h2"),
    ]
    store.insert_docs("demo", docs)
    rows = store.fetch_docs("demo")
    assert len(rows) == 2

    hits = store.search_keyword("demo", "hypertension")
    assert any("hypertension" in r["text"].lower() for r in hits)

    store.close()
