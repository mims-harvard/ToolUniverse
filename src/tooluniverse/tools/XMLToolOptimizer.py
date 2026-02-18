"""
XMLToolOptimizer

Optimizes tools defined in XML format based on test results and quality feedback
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def XMLToolOptimizer(
    xml_tool: str,
    optimization_context: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Optimizes tools defined in XML format based on test results and quality feedback

    Parameters
    ----------
    xml_tool : str
        Current XML-formatted tool definition with code and spec sections
    optimization_context : str
        JSON string containing test results, quality feedback, iteration info, improv...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "XMLToolOptimizer",
            "arguments": {
                "xml_tool": xml_tool,
                "optimization_context": optimization_context,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["XMLToolOptimizer"]
