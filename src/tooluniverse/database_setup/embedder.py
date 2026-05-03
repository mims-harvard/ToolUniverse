"""
Embedder: pluggable text→vector interface for OpenAI, Azure OpenAI, Hugging Face, or local models.

Providers
---------
- "openai"       : OpenAI Embeddings API (model from env or argument)
- "azure"        : Azure OpenAI Embeddings (endpoint/api-version from env)
- "huggingface"  : Hugging Face Inference API (HF_TOKEN required)
- "local"        : SentenceTransformers model loaded locally

Behavior
--------
- Batches input texts and retries transient failures with exponential backoff.
- Returns float32 numpy arrays; normalization is left to callers (SearchEngine/pipeline normalize for cosine/IP).
- Does not truncate inputs: upstream caller should chunk very long texts if needed.

See also
--------
- vector_store.py : FAISS index operations
- search.py       : query-time embedding & hybrid orchestration
"""

import os
import time
from typing import List
import numpy as np
from tooluniverse.database_setup.sqlite_store import SQLiteStore
from tooluniverse.database_setup.vector_store import VectorStore


class Embedder:
    """
    Text embedding client with pluggable backends.

    Parameters
    ----------
    provider : {"openai", "azure", "huggingface", "local"}
        Backend to use.
    model : str
        Embedding model or deployment id (Azure uses deployment name).
    batch_size : int, default 100
        Max texts per API/batch call.
    max_retries : int, default 5
        Exponential-backoff retries on transient failures.

    Raises
    ------
    RuntimeError
        Missing credentials for the chosen provider.
    ValueError
        Unknown provider.
    """

    def __init__(
        self, provider: str, model: str, batch_size: int = 100, max_retries: int = 5
    ):
        self.provider = provider
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries

        if provider == "openai":
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("Missing OPENAI_API_KEY")
            self.client = OpenAI(api_key=api_key)

        elif provider == "azure":
            from openai import AzureOpenAI

            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            if not (api_key and endpoint):
                raise RuntimeError(
                    "Missing AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT"
                )
            self.client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=os.getenv("OPENAI_API_VERSION", "2024-12-01-preview"),
                azure_deployment=deployment,
            )

        elif provider == "huggingface":
            from huggingface_hub import InferenceClient

            token = os.getenv("HF_TOKEN")
            if not token:
                raise RuntimeError("Missing HF_TOKEN for Hugging Face Inference API")
            self.client = InferenceClient(token=token)

        elif provider == "local":
            from sentence_transformers import SentenceTransformer

            self.client = SentenceTransformer(model)

        else:
            raise ValueError(f"Unknown provider: {provider}")

    def embed(self, texts: List[str]) -> np.ndarray:
        """Return embeddings for a list of UTF-8 strings."""

        if isinstance(texts, (bytes, str)):
            texts = [texts]

        texts = [t.decode("utf-8") if isinstance(t, bytes) else str(t) for t in texts]

        all_vectors: List[List[float]] = []

        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]

            if self.provider == "openai":
                # OpenAI supports true batching
                retries = 0
                while True:
                    try:
                        resp = self.client.embeddings.create(
                            model=self.model,
                            input=batch,
                        )
                        all_vectors.extend([d.embedding for d in resp.data])
                        break
                    except Exception:
                        retries += 1
                        if retries > self.max_retries:
                            raise
                        time.sleep(2**retries)

            elif self.provider == "azure":
                # Azure DOES NOT support batched inputs — must loop
                for text in batch:
                    retries = 0
                    while True:
                        try:
                            resp = self.client.embeddings.create(
                                model=self.model,  # deployment name
                                input=text,  # SINGLE STRING ONLY
                            )
                            all_vectors.append(resp.data[0].embedding)
                            break
                        except Exception:
                            retries += 1
                            if retries > self.max_retries:
                                raise
                            time.sleep(2**retries)

            elif self.provider == "huggingface":
                for text in batch:
                    emb = self.client.feature_extraction(text, model=self.model)
                    if isinstance(emb[0], list):
                        emb = emb[0]
                    all_vectors.append(emb)

            elif self.provider == "local":
                vecs = self.client.encode(batch, convert_to_numpy=True)
                if vecs.ndim == 1:
                    vecs = np.expand_dims(vecs, 0)
                all_vectors.extend(vecs.tolist())

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        return np.array(all_vectors, dtype="float32")


if __name__ == "__main__":
    store = SQLiteStore("embeddings.db")

    vs = VectorStore("embeddings.db")

    docs = [
        (
            "uuid-3",
            "Hypertension treatment guidelines for adults",
            {"topic": "blood pressure"},
            "hash3",
        ),
        (
            "uuid-4",
            "Diabetes prevention programs in Germany",
            {"topic": "diabetes"},
            "hash4",
        ),
    ]
    store.insert_docs("euhealth", docs)

    # Fetch docs back
    rows = store.fetch_docs("euhealth", limit=2)
    texts = [r["text"] for r in rows]
    doc_ids = [r["id"] for r in rows]

    # Embed them
    provider = os.getenv("EMBED_PROVIDER")
    model = os.getenv("EMBED_MODEL")

    if not provider or not model:
        raise RuntimeError(
            "You must set EMBED_PROVIDER and EMBED_MODEL in your environment or pass them explicitly."
        )

    emb = Embedder(provider=provider, model=model)

    vectors = emb.embed(texts).astype("float32")
    vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12)
    vs.add_embeddings("euhealth", doc_ids, vectors)

    # Query (demo): SearchEngine already normalizes, but for this direct call normalize too
    qvec = emb.embed(["guidelines for hypertension"])[0].astype("float32")
    qvec = qvec / (np.linalg.norm(qvec, keepdims=True) + 1e-12)
    results = vs.search_embeddings("euhealth", qvec, top_k=5)

    print("Search results:", results)
