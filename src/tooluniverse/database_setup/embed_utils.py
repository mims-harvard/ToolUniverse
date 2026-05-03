"""
embed_utils.py — convenience wrappers around Embedder.

Use cases:
- Get vectors from a list of strings with sane defaults.
- Infer model dimension automatically for build pipelines.
"""

from typing import List, Optional
import numpy as np

from tooluniverse.database_setup.embedder import Embedder
from tooluniverse.database_setup.provider_resolver import (
    resolve_provider,
    resolve_model,
)


def _l2(x: np.ndarray) -> np.ndarray:
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-12)


def embed_texts(
    texts: List[str],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    normalize: bool = True,
    batch_size: Optional[int] = None,
) -> np.ndarray:
    """
    Embed a list of texts with minimal config.

    Args:
      texts: list of strings.
      provider: "openai" | "azure" | "huggingface" | "local".
        Defaults from env or available credentials.
      model: embedding model/deployment name. Defaults provider-wise.
      normalize: return L2-normalized vectors (recommended).
      batch_size: override batch size (optional).

    Returns:
      np.ndarray of shape (N, D) float32
    """
    prov = resolve_provider(provider)
    mdl = resolve_model(prov, model)
    emb = Embedder(
        provider=prov, model=mdl, batch_size=batch_size or 100, max_retries=5
    )
    vecs = emb.embed(texts).astype("float32")
    return _l2(vecs) if normalize else vecs


def get_model_dim(provider: Optional[str] = None, model: Optional[str] = None) -> int:
    """
    Probe the embedding dimension for the current provider/model.
    Useful when you need `embed_dim` but don't want to hardcode it.
    """
    v = embed_texts(["_dim_probe_"], provider=provider, model=model, normalize=False)
    return int(v.shape[1])


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Probe embedding model dimension")
    p.add_argument(
        "--provider",
        required=True,
        help="Embedding provider (openai|azure|huggingface|local)",
    )
    p.add_argument("--model", required=True, help="Embedding model/deployment name")
    args = p.parse_args()

    dim = get_model_dim(provider=args.provider, model=args.model)
    print(dim)
