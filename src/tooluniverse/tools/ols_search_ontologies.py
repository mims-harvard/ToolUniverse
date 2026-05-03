"""
ols_search_ontologies

Search for ontologies in OLS
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_search_ontologies(
    operation: Optional[str] = None,
    search: Optional[str] = None,
    page: Optional[int] = 0,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for ontologies in OLS

    Parameters
    ----------
    operation : str
        The operation to perform (search_ontologies)
    search : str
        Search query for ontologies (optional)
    page : int
        Page number (default: 0)
    size : int
        Number of results per page (default: 20)
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
            "operation": operation,
            "search": search,
            "page": page,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_search_ontologies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_search_ontologies"]
