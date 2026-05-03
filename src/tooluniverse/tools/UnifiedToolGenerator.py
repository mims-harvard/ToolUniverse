"""
UnifiedToolGenerator

Generates complete ToolUniverse tools using simplified XML format that simultaneously creates bot...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UnifiedToolGenerator(
    tool_description: str,
    reference_info: str,
    xml_template: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Generates complete ToolUniverse tools using simplified XML format that simultaneously creates bot...

    Parameters
    ----------
    tool_description : str
        Description of the desired tool functionality
    reference_info : str
        JSON string containing curated reference information including API documentat...
    xml_template : str
        XML template example showing the expected format with code and spec sections
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "tool_description": tool_description,
            "reference_info": reference_info,
            "xml_template": xml_template,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UnifiedToolGenerator",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UnifiedToolGenerator"]
