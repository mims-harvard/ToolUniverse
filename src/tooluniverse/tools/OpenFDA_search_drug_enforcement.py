"""
OpenFDA_search_drug_enforcement

Search the FDA drug enforcement (recall) database via openFDA. Contains drug recalls, withdrawals...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_drug_enforcement(
    search: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    count: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the FDA drug enforcement (recall) database via openFDA. Contains drug recalls, withdrawals...

    Parameters
    ----------
    search : str | Any
        Lucene query for drug recalls (e.g., 'classification:"Class I"', 'status:Ongo...
    limit : int | Any
        Maximum number of results (default 5, max 100)
    count : str | Any
        Field to count by for frequency analysis (e.g., 'classification', 'recalling_...
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
            "name": "OpenFDA_search_drug_enforcement",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenFDA_search_drug_enforcement"]
