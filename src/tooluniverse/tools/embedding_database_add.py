"""
embedding_database_add

Append documents to an existing per-collection datastore (<name>.db + <name>.faiss). Uses the sam...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def embedding_database_add(
    database_name: str,
    documents: list[str],
    action: Optional[str] = None,
    metadata: Optional[list[Any]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Append documents to an existing per-collection datastore (<name>.db + <name>.faiss). Uses the sam...

    Parameters
    ----------
    action : str

    database_name : str
        Existing collection/database name
    documents : list[str]
        List of new document texts to embed and add
    metadata : list[Any]
        Optional metadata per document (must match length of documents if provided)
    provider : str
        Embedding backend override. If omitted, falls back to collection/env.
    model : str
        Embedding model/deployment id override. If omitted, uses collection model or ...
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
    if metadata is None:
        metadata = []
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "action": action,
            "database_name": database_name,
            "documents": documents,
            "metadata": metadata,
            "provider": provider,
            "model": model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "embedding_database_add",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["embedding_database_add"]
