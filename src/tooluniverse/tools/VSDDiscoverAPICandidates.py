"""
VSDDiscoverAPICandidates

Search one or more explicit public catalogs for API-ready data endpoints and OpenAPI specificatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VSDDiscoverAPICandidates(
    query: str,
    limit: Optional[int] = 10,
    providers: Optional[list[str]] = None,
    exclude_registered: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search one or more explicit public catalogs for API-ready data endpoints and OpenAPI specificatio...

    Parameters
    ----------
    query : str
        Research capability or dataset need, such as active cancer clinical trials by...
    limit : int
        Maximum number of non-executable candidates to return.
    providers : list[str]
        Optional explicit catalog set. Omit for the backward-compatible Socrata searc...
    exclude_registered : bool
        For multi-catalog discovery, remove query-free endpoint candidates already co...
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
            "limit": limit,
            "providers": providers,
            "exclude_registered": exclude_registered,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VSDDiscoverAPICandidates",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VSDDiscoverAPICandidates"]
