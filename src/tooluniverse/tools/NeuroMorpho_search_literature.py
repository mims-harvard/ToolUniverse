"""
NeuroMorpho_search_literature

Search source-publication (literature) records linked to NeuroMorpho neuron reconstructions, sear...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroMorpho_search_literature(
    query_value: str,
    query_field: Optional[str] = "brainRegion",
    page: Optional[int] = None,
    size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search source-publication (literature) records linked to NeuroMorpho neuron reconstructions, sear...

    Parameters
    ----------
    query_field : str
        Field to search. Neuroscience-specific options: 'brainRegion', 'cellType', 't...
    query_value : str
        Value to match for the chosen field. Examples: 'hippocampus' (brainRegion), '...
    page : int
        Page number for pagination (0-indexed). Default: 0.
    size : int
        Number of articles per page (max 500). Default: 20.
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
        for k, v in {
            "query_field": query_field,
            "query_value": query_value,
            "page": page,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NeuroMorpho_search_literature",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroMorpho_search_literature"]
