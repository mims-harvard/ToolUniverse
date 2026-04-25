"""
UniProtLocations_search

Search UniProt subcellular locations by name or keyword. Find cellular compartments, organelles, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtLocations_search(
    query: str,
    size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search UniProt subcellular locations by name or keyword. Find cellular compartments, organelles, ...

    Parameters
    ----------
    query : str
        Search query for subcellular locations. Examples: 'nucleus', 'membrane', 'mit...
    size : int
        Maximum number of results to return (default: 10, max: 50).
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
    _args = {k: v for k, v in {
        "query": query,
                "size": size
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProtLocations_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["UniProtLocations_search"]
