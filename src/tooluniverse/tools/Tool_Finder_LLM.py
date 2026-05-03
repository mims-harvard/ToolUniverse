"""
Tool_Finder_LLM

LLM-based tool finder that uses natural language processing to intelligently select relevant tool...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Tool_Finder_LLM(
    description: str,
    limit: Optional[int] = None,
    picked_tool_names: Optional[list[str]] = None,
    return_call_result: Optional[bool] = None,
    categories: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    LLM-based tool finder that uses natural language processing to intelligently select relevant tool...

    Parameters
    ----------
    description : str
        The description of the tool capability required.
    limit : int
        The number of tools to retrieve (default: 10)
    picked_tool_names : list[str]
        Pre-selected tool names to process. If provided, tool selection will skip the...
    return_call_result : bool
        Whether to return both prompts and tool names. If false, returns only tool pr...
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
            "description": description,
            "limit": limit,
            "picked_tool_names": picked_tool_names,
            "return_call_result": return_call_result,
            "categories": categories,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Tool_Finder_LLM",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Tool_Finder_LLM"]
