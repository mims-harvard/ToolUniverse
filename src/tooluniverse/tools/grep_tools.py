"""
grep_tools

Search tools using simple text matching or regex patterns. Supports both simple text search (defa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def grep_tools(
    pattern: str,
    field: Optional[str] = "name",
    search_mode: Optional[str] = "text",
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    categories: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search tools using simple text matching or regex patterns. Supports both simple text search (defa...

    Parameters
    ----------
    pattern : str
        Search pattern (text or regex depending on search_mode)
    field : str
        Field to search in: name, description, type, or category
    search_mode : str
        Search mode: 'text' for simple case-insensitive text matching (default, agent...
    limit : int
        Maximum number of tools to return (default: 100)
    offset : int
        Number of tools to skip (optional, for pagination, default: 0)
    categories : list[str]
        Optional list of tool categories to filter by
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
            "pattern": pattern,
            "field": field,
            "search_mode": search_mode,
            "limit": limit,
            "offset": offset,
            "categories": categories,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "grep_tools",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["grep_tools"]
