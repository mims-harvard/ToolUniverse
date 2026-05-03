"""
execute_tool

Execute a ToolUniverse tool directly with custom arguments. This is the primary way to run any to...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def execute_tool(
    tool_name: str,
    arguments: Optional[dict[str, Any] | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Execute a ToolUniverse tool directly with custom arguments. This is the primary way to run any to...

    Parameters
    ----------
    tool_name : str
        Name of the tool to execute (e.g., 'example_tool_name')
    arguments : dict[str, Any] | str
        Tool arguments as either (1) a JSON object dictionary or (2) a JSON string th...
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
        for k, v in {"tool_name": tool_name, "arguments": arguments}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "execute_tool",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["execute_tool"]
