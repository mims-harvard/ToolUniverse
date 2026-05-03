"""
FlyMine_search

Search FlyMine, the InterMine data warehouse for Drosophila melanogaster (fruit fly) genomics dat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FlyMine_search(
    q: str,
    size: Optional[int] = 10,
    format: Optional[str] = "json",
    facet_Category: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FlyMine, the InterMine data warehouse for Drosophila melanogaster (fruit fly) genomics dat...

    Parameters
    ----------
    q : str
        Search query: gene symbol (e.g., 'dpp', 'Notch', 'hedgehog'), protein name, d...
    size : int
        Number of results to return (default: 10, max: 100).
    format : str
        Response format. Must be 'json'.
    facet_Category : str
        Filter by entity category. Options: 'Gene', 'Protein', 'Publication', 'Protei...
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
            "q": q,
            "size": size,
            "format": format,
            "facet_Category": facet_Category,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FlyMine_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FlyMine_search"]
