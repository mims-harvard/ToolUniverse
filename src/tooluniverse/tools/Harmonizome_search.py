"""
Harmonizome_search

Search Harmonizome across genes, datasets, or attributes. Results are recoverably paginated: star...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Harmonizome_search(
    query: str,
    entity_type: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search Harmonizome across genes, datasets, or attributes. Results are recoverably paginated: star...

    Parameters
    ----------
    query : str
        Search query. Examples: 'TP53', 'BRCA1', 'kinase', 'expression', 'pathway'.
    entity_type : str
        What to search for: 'gene' (default), 'dataset', or 'attribute'.
    limit : int
        Maximum results to return (default: 20).
    offset : int
        Zero-based result offset. Continue with metadata.next_offset.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "entity_type": entity_type,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Harmonizome_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Harmonizome_search"]
