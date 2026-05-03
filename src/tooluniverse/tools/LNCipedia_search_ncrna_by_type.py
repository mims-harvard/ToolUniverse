"""
LNCipedia_search_ncrna_by_type

Search for any type of non-coding RNA by RNA type classification. Supports all RNA types in RNAce...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LNCipedia_search_ncrna_by_type(
    query: str,
    rna_type: Optional[str] = None,
    species: Optional[str] = None,
    size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for any type of non-coding RNA by RNA type classification. Supports all RNA types in RNAce...

    Parameters
    ----------
    query : str
        Search query: gene name, keyword, or accession. Use '*' for all entries of th...
    rna_type : str
        RNA type filter: miRNA, lncRNA, rRNA, tRNA, snRNA, snoRNA, piRNA, pre_miRNA, ...
    species : str
        Species name filter (e.g., 'Homo sapiens'). Leave empty for all species.
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "rna_type": rna_type,
            "species": species,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LNCipedia_search_ncrna_by_type",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LNCipedia_search_ncrna_by_type"]
