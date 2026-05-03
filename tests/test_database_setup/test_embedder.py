import os
import pytest
from tooluniverse.database_setup.embedder import Embedder

@pytest.mark.api
def test_embedder_real_backend_smoke():
    provider = os.getenv("EMBED_PROVIDER")
    model = os.getenv("EMBED_MODEL") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not provider or not model:
        pytest.skip("Set EMBED_PROVIDER and EMBED_MODEL (or AZURE_OPENAI_DEPLOYMENT).")

    emb = Embedder(provider=provider, model=model)
    vecs = emb.embed(["hello world"])
    assert vecs.shape[0] == 1 and vecs.shape[1] > 0
