"""
mcp_auto_loader_expert_feedback

Automatically discover and load all tools from Human Expert Feedback MCP Server. Provides tools f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def mcp_auto_loader_expert_feedback(
    operation: str,
    tool_name: Optional[str] = None,
    tool_arguments: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Automatically discover and load all tools from Human Expert Feedback MCP Server. Provides tools f...

    Parameters
    ----------
    operation : str
        Which of run()'s three branches to take: list the tools this expert-feedback ...
    tool_name : str
        Name of the server-side tool to call, as `discover` reports it. Required when...
    tool_arguments : dict[str, Any]
        Arguments for that tool, matching the inputSchema `discover` returned for it....
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
            "tool_name": tool_name,
            "tool_arguments": tool_arguments,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "mcp_auto_loader_expert_feedback",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["mcp_auto_loader_expert_feedback"]
