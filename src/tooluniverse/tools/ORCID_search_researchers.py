"""
ORCID_search_researchers

Search ORCID registry for researchers by keyword query. Returns ORCID iDs matching the search. Su...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ORCID_search_researchers(
    operation: str,
    query: str,
    start: Optional[int] = 0,
    rows: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search ORCID registry for researchers by keyword query. Returns ORCID iDs matching the search. Su...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Search query (e.g., 'BRCA1 cancer genetics', 'Harvard genomics')
    start : int
        Pagination offset (0-based)
    rows : int
        Number of results to return
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
            "operation": operation,
            "query": query,
            "start": start,
            "rows": rows,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ORCID_search_researchers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ORCID_search_researchers"]
