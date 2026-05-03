"""
ToolMetadataGenerationPipeline

Generates standardized metadata for a batch of ToolUniverse tool configurations by calling ToolMe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolMetadataGenerationPipeline(
    tool_configs: list[Any],
    tool_type_mappings: Optional[dict[str, Any]] = None,
    add_existing_tooluniverse_labels: Optional[bool] = True,
    max_new_tooluniverse_labels: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Generates standardized metadata for a batch of ToolUniverse tool configurations by calling ToolMe...

    Parameters
    ----------
    tool_configs : list[Any]
        List of raw tool configuration JSON objects to extract and standardize metada...
    tool_type_mappings : dict[str, Any]
        Mapping of simplified toolType (keys) to lists of tool 'type' values belongin...
    add_existing_tooluniverse_labels : bool
        Whether to include labels from existing ToolUniverse tools when labeling the ...
    max_new_tooluniverse_labels : int
        The maximum number of new ToolUniverse labels to use in the metadata configs ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error
    if tool_type_mappings is None:
        tool_type_mappings = {}
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "tool_configs": tool_configs,
            "tool_type_mappings": tool_type_mappings,
            "add_existing_tooluniverse_labels": add_existing_tooluniverse_labels,
            "max_new_tooluniverse_labels": max_new_tooluniverse_labels,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ToolMetadataGenerationPipeline",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolMetadataGenerationPipeline"]
