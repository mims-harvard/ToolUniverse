"""
UniProtTaxonomy_search

Search for taxonomic entries in UniProt by name, scientific name, or common name. Returns matchin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtTaxonomy_search(
    query: str,
    size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for taxonomic entries in UniProt by name, scientific name, or common name. Returns matchin...

    Parameters
    ----------
    query : str
        Search query (species name, common name, or partial match). Examples: 'homo s...
    size : int
        Maximum number of results. Default 10, max 500.
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
    _args = {k: v for k, v in {"query": query, "size": size}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProtTaxonomy_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtTaxonomy_search"]
