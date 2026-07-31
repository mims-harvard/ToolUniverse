"""
BioSamples_get_facets

Faceted aggregation discovery over EBI BioSamples: given a free-text query, return the available ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioSamples_get_facets(
    text: str,
    max_values: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Faceted aggregation discovery over EBI BioSamples: given a free-text query, return the available ...

    Parameters
    ----------
    text : str
        Free-text query to compute facets over. Examples: 'cancer', 'liver', 'Homo sa...
    max_values : int
        Maximum number of top values to return per facet (1-50, default 10).
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
        for k, v in {"text": text, "max_values": max_values}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioSamples_get_facets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioSamples_get_facets"]
