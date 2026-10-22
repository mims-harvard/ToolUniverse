"""
NCBIGene_search

Search NCBI Gene using ESearch with explicit offset pagination and normalized exact metadata. Con...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIGene_search(
    term: str,
    retmax: Optional[int] = 10,
    retstart: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NCBI Gene using ESearch with explicit offset pagination and normalized exact metadata. Con...

    Parameters
    ----------
    term : str
        Search query. Use gene symbol with organism filter for best results. Format: ...
    retmax : int
        Page size (1-100).
    retstart : int
        Zero-based result offset. Use esearchresult.retstart plus the number of retur...
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
        for k, v in {"term": term, "retmax": retmax, "retstart": retstart}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBIGene_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIGene_search"]
