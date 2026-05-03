"""
NCBIDatasets_suggest_taxonomy

Suggest taxonomic names matching a query string. Searches NCBI Taxonomy for organisms by partial ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIDatasets_suggest_taxonomy(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Suggest taxonomic names matching a query string. Searches NCBI Taxonomy for organisms by partial ...

    Parameters
    ----------
    query : str
        Partial organism name to search. Examples: 'drosophila', 'escherichia', 'arab...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NCBIDatasets_suggest_taxonomy",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIDatasets_suggest_taxonomy"]
