"""
UniProtRef_search_proteomes

Search UniProt reference proteomes with official cursor pagination. Returns proteome IDs, organis...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtRef_search_proteomes(
    query: str,
    size: Optional[int] = None,
    cursor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search UniProt reference proteomes with official cursor pagination. Returns proteome IDs, organis...

    Parameters
    ----------
    query : str
        Search query for proteomes. Can be organism name or taxon ID. Examples: 'homo...
    size : int
        Results per official cursor page (default 10, maximum 500). Invalid values re...
    cursor : str
        Opaque cursor from metadata.next_cursor. Omit for the first page.
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
        for k, v in {"query": query, "size": size, "cursor": cursor}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProtRef_search_proteomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtRef_search_proteomes"]
