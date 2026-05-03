"""
ToolUniverse_get_usage_tips

Return concise usage tips for the ToolUniverse SDK. Use topic='all' (default) to get all tips, or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolUniverse_get_usage_tips(
    topic: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Return concise usage tips for the ToolUniverse SDK. Use topic='all' (default) to get all tips, or...

    Parameters
    ----------
    topic : str
        Topic to filter tips. One of: 'loading', 'running', 'searching', 'workspace',...
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
    _args = {k: v for k, v in {"topic": topic}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ToolUniverse_get_usage_tips",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolUniverse_get_usage_tips"]
