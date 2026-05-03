"""
PathwayCommons_get_pathway

Get detailed pathway information from Pathway Commons by URI. Returns the pathway name, participa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PathwayCommons_get_pathway(
    uri: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed pathway information from Pathway Commons by URI. Returns the pathway name, participa...

    Parameters
    ----------
    uri : str
        Pathway Commons URI from search results, e.g., http://bioregistry.io/reactome...
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
    _args = {k: v for k, v in {"uri": uri}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PathwayCommons_get_pathway",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PathwayCommons_get_pathway"]
