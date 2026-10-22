"""
WikiPathways_search

Search pathway titles in the current WikiPathways SPARQL dataset. Results are recoverably paginat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WikiPathways_search(
    query: str,
    organism: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search pathway titles in the current WikiPathways SPARQL dataset. Results are recoverably paginat...

    Parameters
    ----------
    query : str
        Free-text query (keywords, gene symbols, processes), e.g., 'p53', 'glycolysis'.
    organism : str
        Organism filter (scientific name), e.g., 'Homo sapiens'.
    limit : int
        Number of pathways per page.
    offset : int
        Zero-based result offset; continue with metadata.next_offset.
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
            "organism": organism,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WikiPathways_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WikiPathways_search"]
