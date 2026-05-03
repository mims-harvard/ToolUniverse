"""
BioTools_search

Search the ELIXIR Bio.tools registry for bioinformatics software tools, databases, and web servic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioTools_search(
    q: str,
    page: Optional[int] = 1,
    size: Optional[int] = 10,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the ELIXIR Bio.tools registry for bioinformatics software tools, databases, and web servic...

    Parameters
    ----------
    q : str
        Free-text search query. Searches across tool names, descriptions, and topics....
    page : int
        Page number for paginated results (1-based). Default: 1.
    size : int
        Number of results per page (1-50). Default: 10.
    format : str
        Response format. Must be 'json'.
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
        for k, v in {"q": q, "page": page, "size": size, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioTools_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioTools_search"]
