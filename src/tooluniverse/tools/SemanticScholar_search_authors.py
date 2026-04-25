"""
SemanticScholar_search_authors

Search for researchers/authors on Semantic Scholar by name. Returns author IDs, names, h-index, c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SemanticScholar_search_authors(
    query: str,
    limit: Optional[int] = 5,
    fields: Optional[str] = 'name,hIndex,citationCount,paperCount,affiliations',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for researchers/authors on Semantic Scholar by name. Returns author IDs, names, h-index, c...

    Parameters
    ----------
    query : str
        Author name to search for (e.g., 'Jennifer Doudna', 'Oren Etzioni', 'Yann LeC...
    limit : int
        Maximum number of results (default 5, max 1000)
    fields : str
        Comma-separated fields: name,hIndex,citationCount,paperCount,affiliations
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
    _args = {k: v for k, v in {
        "query": query,
                "limit": limit,
                "fields": fields
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SemanticScholar_search_authors",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["SemanticScholar_search_authors"]
