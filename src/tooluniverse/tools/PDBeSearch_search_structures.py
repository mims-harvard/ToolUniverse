"""
PDBeSearch_search_structures

Search PDB structures through PDBe's Solr search interface by keyword, protein name, or gene name...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDBeSearch_search_structures(
    query: str,
    limit: Optional[int] = None,
    sort_by: Optional[str] = "relevance",
    offset: Optional[int] = 0,
    max_rows_scanned: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PDB structures through PDBe's Solr search interface by keyword, protein name, or gene name...

    Parameters
    ----------
    query : str
        Search query - protein name, gene name, or keyword. Supports Solr syntax. Exa...
    limit : int
        Unique PDB entries per page (1-1000, default 10). Invalid values return an er...
    sort_by : str
        Result ordering: 'relevance' (default) puts the best text match first with re...
    offset : int
        Zero-based offset after deduplication by pdb_id. Continue with metadata.next_...
    max_rows_scanned : int
        Optional entity-level Solr scan budget used to fill the requested unique-PDB ...
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
            "limit": limit,
            "sort_by": sort_by,
            "offset": offset,
            "max_rows_scanned": max_rows_scanned,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDBeSearch_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDBeSearch_search_structures"]
