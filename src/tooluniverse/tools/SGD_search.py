"""
SGD_search

Search SGD across all data types (genes, GO terms, phenotypes, references, alleles, diseases, com...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SGD_search(
    query: str,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search SGD across all data types (genes, GO terms, phenotypes, references, alleles, diseases, com...

    Parameters
    ----------
    query : str
        Search query string. Examples: 'GAL4', 'cell cycle', 'sporulation'.
    category : str
        Filter by category. Options: 'locus', 'reference', 'biological_process', 'mol...
    limit : int
        Maximum results to return (default 10, max 50).
    offset : int
        Pagination offset (default 0).
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "category": category,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SGD_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SGD_search"]
