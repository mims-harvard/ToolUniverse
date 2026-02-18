"""
ReferenceInfoAnalyzer

Analyzes and curates reference information to provide high-quality context for tool generation
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReferenceInfoAnalyzer(
    tool_description: str,
    raw_reference_info: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyzes and curates reference information to provide high-quality context for tool generation

    Parameters
    ----------
    tool_description : str
        Description of the tool being generated
    raw_reference_info : str
        JSON string containing raw reference information from web search and package ...
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
            "name": "ReferenceInfoAnalyzer",
            "arguments": {
                "tool_description": tool_description,
                "raw_reference_info": raw_reference_info,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReferenceInfoAnalyzer"]
