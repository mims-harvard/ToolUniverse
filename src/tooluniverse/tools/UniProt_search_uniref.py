"""
UniProt_search_uniref

Search UniRef clusters. Returns clusters matching the query. Use this to find UniRef clusters for...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_search_uniref(
    query: str,
    cluster_type: Optional[str] = "UniRef50",
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search UniRef clusters. Returns clusters matching the query. Use this to find UniRef clusters for...

    Parameters
    ----------
    query : str
        Search query. Examples: 'P04637' (protein accession), 'name:TP53', 'organism_...
    cluster_type : str
        UniRef cluster type: UniRef100 (100% identity), UniRef90 (90% identity), UniR...
    limit : int
        Maximum number of results to return (default: 25, max: 500)
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
            "cluster_type": cluster_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProt_search_uniref",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_search_uniref"]
