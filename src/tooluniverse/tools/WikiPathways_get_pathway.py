"""
WikiPathways_get_pathway

Fetch pathway content by WPID. format='json' (default) returns structured metadata (uri, title, o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WikiPathways_get_pathway(
    wpid: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch pathway content by WPID. format='json' (default) returns structured metadata (uri, title, o...

    Parameters
    ----------
    wpid : str
        WikiPathways identifier (e.g., 'WP254').
    format : str
        Response format: 'json' for structured, 'gpml' for GPML XML.
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"wpid": wpid, "format": format}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "WikiPathways_get_pathway",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WikiPathways_get_pathway"]
