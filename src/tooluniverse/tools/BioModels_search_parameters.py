"""
BioModels_search_parameters

Search parameters within BioModels entries using the parameter service's size/start pagination. C...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioModels_search_parameters(
    query: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search parameters within BioModels entries using the parameter service's size/start pagination. C...

    Parameters
    ----------
    query : str
        Search query for parameters (e.g., parameter name like 'k1', 'Km', or biologi...
    limit : int
        Maximum number of results to return (default: 10, max: 100).
    offset : int
        Zero-based parameter-record offset. Continue with metadata.next_offset.
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
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioModels_search_parameters",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioModels_search_parameters"]
