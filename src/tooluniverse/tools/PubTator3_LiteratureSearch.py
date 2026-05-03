"""
PubTator3_LiteratureSearch

Find PubMed articles that match a keyword, a PubTator entity ID (e.g. “@GENE_BRAF”), or an entity...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubTator3_LiteratureSearch(
    query: str,
    page: Optional[int] = 0,
    page_size: Optional[int] = 10,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find PubMed articles that match a keyword, a PubTator entity ID (e.g. “@GENE_BRAF”), or an entity...

    Parameters
    ----------
    query : str
        What you want to search for. This can be plain keywords, a single PubTator ID...
    page : int
        Zero-based results page (optional; default = 0).
    page_size : int
        How many PMIDs to return per page (optional; default = 10; note: the PubTator...
    limit : int
        Maximum number of results to return (applied client-side). The PubTator3 API ...
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
            "page": page,
            "page_size": page_size,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubTator3_LiteratureSearch",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubTator3_LiteratureSearch"]
