"""
get_tool_page_url

Get the public ToolUniverse web page URL for a tool by its exact tool name. Returns the URL of th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_tool_page_url(
    tool_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the public ToolUniverse web page URL for a tool by its exact tool name. Returns the URL of th...

    Parameters
    ----------
    tool_name : str
        Exact ToolUniverse tool name (e.g. 'ADA_list_standards_sections', 'PubMed_sea...
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
    _args = {k: v for k, v in {"tool_name": tool_name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "get_tool_page_url",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_tool_page_url"]
