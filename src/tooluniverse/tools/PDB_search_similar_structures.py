"""
PDB_search_similar_structures

Search RCSB PDB by protein sequence, strict structure-shape matching, or text. Results use exact ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDB_search_similar_structures(
    query: str,
    search_type: Optional[str] = "sequence",
    similarity_threshold: Optional[float] = 0.7,
    max_results: Optional[int] = 20,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search RCSB PDB by protein sequence, strict structure-shape matching, or text. Results use exact ...

    Parameters
    ----------
    query : str
        PDB ID (e.g., '1ABC'), protein sequence (amino acids), or search text (e.g., ...
    search_type : str
        Type of search: 'sequence' for sequence-based similarity search, 'structure' ...
    similarity_threshold : float
        Sequence identity cutoff from 0 to 1. Applied only for sequence search. RCSB ...
    max_results : int
        Number of results per page (1-100). Invalid values are rejected rather than s...
    start : int
        Zero-based result offset using RCSB's official paginate.start parameter. Cont...
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
            "start": start,
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
