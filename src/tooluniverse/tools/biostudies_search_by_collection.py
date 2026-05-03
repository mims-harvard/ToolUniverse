"""
biostudies_search_by_collection

Search BioStudies by specific collection (e.g., ArrayExpress, BioImages, EuropePMC). Collections ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def biostudies_search_by_collection(
    collection: str,
    query: Optional[str] = None,
    pageSize: Optional[int] = 10,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search BioStudies by specific collection (e.g., ArrayExpress, BioImages, EuropePMC). Collections ...

    Parameters
    ----------
    query : str
        Search query within the collection
    collection : str
        Collection name (e.g., 'arrayexpress', 'bioimages', 'biomodels')
    pageSize : int
        Number of results per page (default: 10, max: 100)
    page : int
        Page number (default: 1)
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
            "collection": collection,
            "pageSize": pageSize,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "biostudies_search_by_collection",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["biostudies_search_by_collection"]
