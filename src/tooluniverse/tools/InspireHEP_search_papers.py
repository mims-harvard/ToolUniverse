"""
InspireHEP_search_papers

Search high-energy physics literature in the INSPIRE-HEP database, the premier repository for phy...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InspireHEP_search_papers(
    q: str,
    sort: Optional[str | Any] = None,
    size: Optional[int | Any] = None,
    fields: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search high-energy physics literature in the INSPIRE-HEP database, the premier repository for phy...

    Parameters
    ----------
    q : str
        INSPIRE search query. Examples: 'higgs boson discovery', 'author:einstein', '...
    sort : str | Any
        Sort order. Values: 'mostrecent' (default), 'mostcited'. Examples: 'mostcited...
    size : int | Any
        Number of results (1-25). Default: 10
    fields : str | Any
        Comma-separated fields to return. Default includes titles, authors, abstract,...
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
    _args = {k: v for k, v in {
        "q": q,
                "sort": sort,
                "size": size,
                "fields": fields
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "InspireHEP_search_papers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["InspireHEP_search_papers"]
