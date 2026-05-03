"""
PDB_search_similar_structures

Search for protein structures similar to a given PDB ID or sequence using RCSB PDB structure simi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDB_search_similar_structures(
    query: str,
    search_type: Optional[str] = "sequence",
    similarity_threshold: Optional[float] = 0.7,
    max_results: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for protein structures similar to a given PDB ID or sequence using RCSB PDB structure simi...

    Parameters
    ----------
    query : str
        PDB ID (e.g., '1ABC'), protein sequence (amino acids), or search text (e.g., ...
    search_type : str
        Type of search: 'sequence' for sequence-based similarity search, 'structure' ...
    similarity_threshold : float
        Similarity threshold (0-1). Higher values return more similar structures. Val...
    max_results : int
        Maximum number of results to return (1-100). Values outside this range will b...
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
            "query": query,
            "search_type": search_type,
            "similarity_threshold": similarity_threshold,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDB_search_similar_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDB_search_similar_structures"]
