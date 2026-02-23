"""
BioTools_get_tool

Get detailed information about a specific bioinformatics tool from the ELIXIR Bio.tools registry ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioTools_get_tool(
    biotoolsID: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific bioinformatics tool from the ELIXIR Bio.tools registry ...

    Parameters
    ----------
    biotoolsID : str
        The unique Bio.tools identifier for the tool. Use lowercase. Examples: 'samto...
    format : str
        Response format. Must be 'json'.
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

    return get_shared_client().run_one_function(
        {
            "name": "BioTools_get_tool",
            "arguments": {"biotoolsID": biotoolsID, "format": format},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioTools_get_tool"]
