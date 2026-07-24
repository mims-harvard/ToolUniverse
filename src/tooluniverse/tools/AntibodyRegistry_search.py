"""
AntibodyRegistry_search

Search the Antibody Registry (antibodyregistry.org, a SciCrunch/RRID resource of 3M+ research ant...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AntibodyRegistry_search(
    query: str,
    size: Optional[int] = 10,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Antibody Registry (antibodyregistry.org, a SciCrunch/RRID resource of 3M+ research ant...

    Parameters
    ----------
    query : str
        Full-text search term: a target (e.g. 'GFAP', 'CD3'), antibody name, vendor, ...
    size : int
        Number of results to return (1-100, default 10).
    page : int
        Result page, starting at 1 (default 1).
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
        for k, v in {"query": query, "size": size, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AntibodyRegistry_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AntibodyRegistry_search"]
