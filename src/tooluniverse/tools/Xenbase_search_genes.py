"""
Xenbase_search_genes

Search for Xenopus (frog) genes in Xenbase via the Alliance of Genome Resources API. Returns gene...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Xenbase_search_genes(
    query: str,
    species: Optional[str] = "",
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for Xenopus (frog) genes in Xenbase via the Alliance of Genome Resources API. Returns gene...

    Parameters
    ----------
    query : str
        Gene symbol or name to search. Examples: 'tp53', 'pax6', 'sox2', 'bmp4', 'wnt...
    species : str
        Optional species filter: 'tropicalis' for X. tropicalis, 'laevis' for X. laev...
    limit : int
        Maximum number of results to return. Default: 10.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"query": query, "species": species, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Xenbase_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Xenbase_search_genes"]
