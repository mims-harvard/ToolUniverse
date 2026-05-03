import os
import numpy as np
import pytest

from tooluniverse.database_setup import pipeline
from tooluniverse.database_setup.embedder import Embedder

def _resolve_provider_model_or_skip():
    prov = os.getenv("EMBED_PROVIDER")
    model = os.getenv("EMBED_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not prov or not model:
        pytest.skip("Set EMBED_PROVIDER and EMBED_MODEL/AZURE_OPENAI_DEPLOYMENT")
    return prov, model

@pytest.mark.api
def test_build_search_roundtrip(tmp_path):
    db = str(tmp_path / "demo.db")
    provider, model = _resolve_provider_model_or_skip()

    # infer dimension for portability across models
    _ = int(Embedder(provider, model).embed(["x"]).shape[1])

    docs = [
        ("uuid-1", "Hypertension treatment guidelines", {"title": "HTN"}, "h1"),
        ("uuid-2", "Diabetes prevention programs", {"title": "DM"}, "h2"),
    ]

    pipeline.build_collection(
        db_path=db,
        collection="demo",
        docs=docs,
        embed_provider=provider,
        embed_model=model,
        overwrite=False,
    )

    res_kw = pipeline.search(db, "demo", "hypertension", method="keyword", top_k=5)
    res_emb = pipeline.search(db, "demo", "hypertension", method="embedding", top_k=5,
                              embed_provider=provider, embed_model=model)
    res_hyb = pipeline.search(db, "demo", "hypertension", method="hybrid", top_k=5, alpha=0.5,
                              embed_provider=provider, embed_model=model)

    assert any("hypertension" in r["text"].lower() for r in res_kw)
    assert len(res_emb) >= 1
    assert len(res_hyb) >= 1
