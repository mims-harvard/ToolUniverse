"""
list_tools

List tools with multiple output modes. Default mode='names' for quick scanning. Recommended workf...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def list_tools(
    mode: Optional[str] = 'names',
    categories: Optional[list[str]] = None,
    fields: Optional[list[str]] = None,
    group_by_category: Optional[bool] = False,
    brief: Optional[bool] = False,
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List tools with multiple output modes. Default mode='names' for quick scanning. Recommended workf...

    Parameters
    ----------
    mode : str
        Output mode (default: 'names'). Warning: non-'names' modes like 'basic'/'summ...
    categories : list[str]
        Optional list of tool categories to filter by (applies to all modes except 'c...
    fields : list[str]
        Required for mode='custom'. List of fields to include (e.g., ["name", "type",...
    group_by_category : bool
        Whether to group results by category (only for mode='names', 'basic', or 'sum...
    brief : bool
        Whether to truncate description to brief (only for mode='basic' or 'summary')
    limit : int
        Maximum number of tools to return (optional, for pagination)
    offset : int
        Number of tools to skip (optional, for pagination, default: 0)
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
    _args = {k: v for k, v in {
        "mode": mode,
                "categories": categories,
                "fields": fields,
                "group_by_category": group_by_category,
                "brief": brief,
                "limit": limit,
                "offset": offset
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "list_tools",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["list_tools"]
