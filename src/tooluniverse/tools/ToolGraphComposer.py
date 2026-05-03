"""
ToolGraphComposer

Builds a comprehensive graph of tool compatibility relationships in ToolUniverse. Analyzes all av...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolGraphComposer(
    output_path: str,
    analysis_depth: str,
    min_compatibility_score: int,
    exclude_categories: list[str],
    max_tools_per_category: int,
    force_rebuild: bool,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Builds a comprehensive graph of tool compatibility relationships in ToolUniverse. Analyzes all av...

    Parameters
    ----------
    output_path : str
        Path to save the generated graph files (JSON and pickle formats)
    analysis_depth : str
        Level of compatibility analysis to perform
    min_compatibility_score : int
        Minimum compatibility score to create an edge in the graph
    exclude_categories : list[str]
        Tool categories to exclude from analysis (e.g., ['tool_finder', 'special_tool...
    max_tools_per_category : int
        Maximum number of tools to analyze per category (for performance)
    force_rebuild : bool
        Whether to force rebuild even if cached graph exists
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
            "output_path": output_path,
            "analysis_depth": analysis_depth,
            "min_compatibility_score": min_compatibility_score,
            "exclude_categories": exclude_categories,
            "max_tools_per_category": max_tools_per_category,
            "force_rebuild": force_rebuild,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ToolGraphComposer",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolGraphComposer"]
