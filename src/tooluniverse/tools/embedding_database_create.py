"""
embedding_database_create

Create a per-collection datastore: <name>.db (SQLite) + <name>.faiss (FAISS). Embeds documents us...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def embedding_database_create(
    database_name: str,
    documents: list[str],
    action: Optional[str] = None,
    metadata: Optional[list[Any]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    description: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Create a per-collection datastore: <name>.db (SQLite) + <name>.faiss (FAISS). Embeds documents us...

    Parameters
    ----------
    action : str

    database_name : str
        Collection/database name (produces <name>.db and <name>.faiss)
    documents : list[str]
        List of document texts to embed and store
    metadata : list[Any]
        Optional metadata for each document (must match length of documents if provided)
    provider : str
        Embedding backend. Defaults: EMBED_PROVIDER, else by available creds (azure>o...
    model : str
        Embedding model/deployment id. Defaults: EMBED_MODEL, else provider-specific ...
    description : str
        Optional human-readable description for the collection
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
            "description": description,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "embedding_database_create",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["embedding_database_create"]
