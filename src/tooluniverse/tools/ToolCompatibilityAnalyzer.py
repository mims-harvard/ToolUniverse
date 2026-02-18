"""
ToolCompatibilityAnalyzer

Analyzes two tool specifications to determine if one tool's output can be used as input for anoth...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolCompatibilityAnalyzer(
    source_tool: str,
    target_tool: str,
    analysis_depth: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyzes two tool specifications to determine if one tool's output can be used as input for anoth...

    Parameters
    ----------
    source_tool : str
        The source tool specification (JSON string with name, description, parameter ...
    target_tool : str
        The target tool specification (JSON string with name, description, parameter ...
    analysis_depth : str
        Level of analysis depth - quick for basic compatibility, detailed for paramet...
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

    return get_shared_client().run_one_function(
        {
            "name": "ToolCompatibilityAnalyzer",
            "arguments": {
                "source_tool": source_tool,
                "target_tool": target_tool,
                "analysis_depth": analysis_depth,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolCompatibilityAnalyzer"]
