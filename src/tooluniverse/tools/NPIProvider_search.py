"""
NPIProvider_search

US healthcare provider/organization directory search via the NLM Clinical Table Search Service (N...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NPIProvider_search(
    terms: str,
    organization: Optional[bool] = None,
    max_results: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    US healthcare provider/organization directory search via the NLM Clinical Table Search Service (N...

    Parameters
    ----------
    terms : str
        Provider or organization name to search, e.g. 'Smith', 'Mayo Clinic'.
    organization : bool
        Search organizations (hospitals, clinics) instead of individual providers. De...
    max_results : int
        Maximum number of matches to return (default 20, max 500).
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
            "terms": terms,
            "organization": organization,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NPIProvider_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NPIProvider_search"]
