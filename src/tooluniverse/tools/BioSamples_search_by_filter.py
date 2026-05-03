"""
BioSamples_search_by_filter

Search the EBI BioSamples database with structured attribute filters. More precise than text sear...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioSamples_search_by_filter(
    attribute: str,
    value: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the EBI BioSamples database with structured attribute filters. More precise than text sear...

    Parameters
    ----------
    attribute : str
        Attribute name to filter on. Common attributes: 'organism', 'tissue', 'diseas...
    value : str
        Value to match for the attribute. Examples: 'Homo sapiens', 'liver', 'melanom...
    limit : int | Any
        Maximum results to return (1-50, default 10).
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
    _args = {
        k: v
        for k, v in {"attribute": attribute, "value": value, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioSamples_search_by_filter",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioSamples_search_by_filter"]
