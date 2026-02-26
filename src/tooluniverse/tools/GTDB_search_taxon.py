"""
GTDB_search_taxon

Search the Genome Taxonomy Database (GTDB) for prokaryotic taxa by partial name. GTDB provides a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTDB_search_taxon(
    operation: str,
    query: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Genome Taxonomy Database (GTDB) for prokaryotic taxa by partial name. GTDB provides a ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_taxon)
    query : str
        Partial taxon name to search for (e.g., 'Lachnospiraceae', 'Escherichia', 'Ba...
    limit : int
        Maximum number of results per rank (default: 20, max: 100)
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

    return get_shared_client().run_one_function(
        {
            "name": "GTDB_search_taxon",
            "arguments": {"operation": operation, "query": query, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTDB_search_taxon"]
