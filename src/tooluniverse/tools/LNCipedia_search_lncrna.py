"""
LNCipedia_search_lncrna

Search for long non-coding RNAs (lncRNAs) by name, accession, or keyword using EBI Search over RN...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LNCipedia_search_lncrna(
    query: str,
    species: Optional[str] = None,
    size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for long non-coding RNAs (lncRNAs) by name, accession, or keyword using EBI Search over RN...

    Parameters
    ----------
    query : str
        Search query: lncRNA name (e.g., 'MALAT1', 'HOTAIR'), gene symbol, accession,...
    species : str
        Species name filter (e.g., 'Homo sapiens', 'Mus musculus'). Leave empty for a...
    size : int
        Number of results to return (1-100). Default: 10.
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
            "name": "LNCipedia_search_lncrna",
            "arguments": {"query": query, "species": species, "size": size},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LNCipedia_search_lncrna"]
