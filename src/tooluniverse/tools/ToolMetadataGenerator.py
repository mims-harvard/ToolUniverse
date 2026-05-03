"""
ToolMetadataGenerator

Generates a JSON structure with the metadata of a tool in ToolUniverse, given the JSON configurat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolMetadataGenerator(
    tool_config: str,
    tool_type_mappings: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generates a JSON structure with the metadata of a tool in ToolUniverse, given the JSON configurat...

    Parameters
    ----------
    tool_config : str
        JSON string of the tool configuration to extract metadata from
    tool_type_mappings : dict[str, Any]
        A mapping from a simplified toolType to a list of tool_config.type that fall ...
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
            "tool_config": tool_config,
            "tool_type_mappings": tool_type_mappings,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ToolMetadataGenerator",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolMetadataGenerator"]
