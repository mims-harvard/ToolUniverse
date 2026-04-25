"""
OpenFDA_search_food_enforcement

Search the FDA food enforcement (recall) database via openFDA. Contains food recalls, market with...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_food_enforcement(
    search: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    count: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the FDA food enforcement (recall) database via openFDA. Contains food recalls, market with...

    Parameters
    ----------
    search : str | Any
        Lucene query for food recalls (e.g., 'classification:"Class I"', 'reason_for_...
    limit : int | Any
        Maximum number of results (default 5, max 100)
    count : str | Any
        Field to count by (e.g., 'classification', 'state', 'recalling_firm.exact')
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
        "search": search,
                "limit": limit,
                "count": count
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDA_search_food_enforcement",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenFDA_search_food_enforcement"]
