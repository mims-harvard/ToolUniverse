"""
SASBDB_search

Search SASBDB small-angle scattering database by query term or UniProt accession. UniProt IDs ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SASBDB_search(
    query: str,
    max_results: Optional[int] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search SASBDB small-angle scattering database by query term or UniProt accession. UniProt IDs ret...

    Parameters
    ----------
    query : str
        Search query: UniProt accession (e.g., 'P02769' for BSA) or free-text term. N...
    max_results : int
        Page size when a free-text query falls back to listing the published-entry ca...
    offset : int
        Zero-based catalog offset for free-text fallback results. Continue with next_...
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
            "max_results": max_results,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SASBDB_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SASBDB_search"]
