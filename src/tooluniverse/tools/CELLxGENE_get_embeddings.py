"""
CELLxGENE_get_embeddings

Access pre-calculated cell embeddings (scVI, Geneformer) from CELLxGENE Census. Returns available...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CELLxGENE_get_embeddings(
    operation: str,
    organism: Optional[str] = "Homo sapiens",
    embedding_name: Optional[str] = None,
    census_version: Optional[str] = "stable",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Access pre-calculated cell embeddings (scVI, Geneformer) from CELLxGENE Census. Returns available...

    Parameters
    ----------
    operation : str
        Operation type
    organism : str
        Organism name
    embedding_name : str
        Name of specific embedding to retrieve (omit to list available embeddings)
    census_version : str
        Census version to query. 'stable' (recommended, Long-Term Support release), '...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "organism": organism,
            "embedding_name": embedding_name,
            "census_version": census_version,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CELLxGENE_get_embeddings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CELLxGENE_get_embeddings"]
