"""
embedding_database_search

Semantic search over a per-collection datastore using FAISS (cosine via L2-normalized vectors). S...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def embedding_database_search(
    database_name: str,
    query: str,
    action: Optional[str] = None,
    top_k: Optional[int] = 5,
    filters: Optional[dict[str, Any]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Semantic search over a per-collection datastore using FAISS (cosine via L2-normalized vectors). S...

    Parameters
    ----------
    action : str

    database_name : str
        Collection/database name to search
    query : str
        Query text to embed and search with
    top_k : int
        Number of most similar documents to return
    filters : dict[str, Any]
        Optional metadata filters ('$gte', '$lte', '$in', '$contains', exact match)
    provider : str
        Embedding backend for the query vector. Defaults to collection/env.
    model : str
        Embedding model/deployment id for the query vector. Defaults to collection/env.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error
    if filters is None:
        filters = {}
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "action": action,
            "database_name": database_name,
            "query": query,
            "top_k": top_k,
            "filters": filters,
            "provider": provider,
            "model": model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "embedding_database_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["embedding_database_search"]
