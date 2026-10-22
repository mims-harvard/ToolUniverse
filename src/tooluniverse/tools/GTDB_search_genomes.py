"""
GTDB_search_genomes

Search prokaryotic genomes in GTDB using strict one-based page pagination and pages up to 1000 re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTDB_search_genomes(
    query: str,
    operation: Optional[str] = "search_genomes",
    page: Optional[int] = None,
    items_per_page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search prokaryotic genomes in GTDB using strict one-based page pagination and pages up to 1000 re...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search_genomes)
    query : str
        Search query for organism name (e.g., 'Escherichia', 'Staphylococcus aureus',...
    page : int
        One-based page number (default 1). Never use 0; continue with metadata.next_p...
    items_per_page : int
        Number of results per page (default 10, max 1000).
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
            "operation": operation,
            "query": query,
            "page": page,
            "items_per_page": items_per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTDB_search_genomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTDB_search_genomes"]
