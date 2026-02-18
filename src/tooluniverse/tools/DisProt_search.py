"""
DisProt_search

Search DisProt for intrinsically disordered proteins by text query (gene name, protein name, orga...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisProt_search(
    query: str,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search DisProt for intrinsically disordered proteins by text query (gene name, protein name, orga...

    Parameters
    ----------
    query : str
        Search term: gene name (e.g., 'TP53'), protein name (e.g., 'kinase'), organis...
    page_size : int
        Number of results to return (default 10, max 20).
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
            "name": "DisProt_search",
            "arguments": {"query": query, "page_size": page_size},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisProt_search"]
