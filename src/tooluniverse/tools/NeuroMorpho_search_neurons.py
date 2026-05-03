"""
NeuroMorpho_search_neurons

Search for neurons in NeuroMorpho.Org by species, brain region, cell type, or other attributes. S...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroMorpho_search_neurons(
    query_value: str,
    query_field: Optional[str] = "species",
    filter_field: Optional[str | Any] = None,
    filter_value: Optional[str | Any] = None,
    page: Optional[int] = 0,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for neurons in NeuroMorpho.Org by species, brain region, cell type, or other attributes. S...

    Parameters
    ----------
    query_field : str
        Field to search on. Common fields: 'species', 'brain_region', 'cell_type', 'a...
    query_value : str
        Value to search for. Examples: 'human', 'rat', 'mouse', 'hippocampus', 'pyram...
    filter_field : str | Any
        Optional additional filter field. Example: 'cell_type'.
    filter_value : str | Any
        Value for the filter field. Example: 'pyramidal'.
    page : int
        Page number (0-indexed). Default: 0.
    size : int
        Results per page (max 500). Default: 20.
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
            "filter_field": filter_field,
            "filter_value": filter_value,
            "page": page,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NeuroMorpho_search_neurons",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroMorpho_search_neurons"]
