"""
SynBioHub_search_parts

Search the SynBioHub synthetic biology parts repository for genetic parts and designs by keyword....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SynBioHub_search_parts(
    query: str,
    offset: Optional[int | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the SynBioHub synthetic biology parts repository for genetic parts and designs by keyword....

    Parameters
    ----------
    query : str
        Search query for finding genetic parts. Can include gene names, part function...
    offset : int | Any
        Offset for pagination (default: 0).
    limit : int | Any
        Maximum number of results to return (default: 10, max: 50).
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
        for k, v in {"query": query, "offset": offset, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SynBioHub_search_parts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SynBioHub_search_parts"]
