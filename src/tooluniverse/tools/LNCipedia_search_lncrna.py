"""
LNCipedia_search_lncrna

Search long non-coding RNAs by name, accession, or keyword using EBI Search over RNAcentral. Resu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LNCipedia_search_lncrna(
    query: str,
    species: Optional[str] = None,
    size: Optional[int] = 10,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search long non-coding RNAs by name, accession, or keyword using EBI Search over RNAcentral. Resu...

    Parameters
    ----------
    query : str
        Search query: lncRNA name (e.g., 'MALAT1', 'HOTAIR'), gene symbol, accession,...
    species : str
        Species name filter (e.g., 'Homo sapiens', 'Mus musculus'). Leave empty for a...
    size : int
        Number of results per page (1-100).
    start : int
        Zero-based EBI Search result offset. Continue with next_start.
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
            "species": species,
            "size": size,
            "start": start,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LNCipedia_search_lncrna",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LNCipedia_search_lncrna"]
