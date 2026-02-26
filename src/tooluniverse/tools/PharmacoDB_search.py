"""
PharmacoDB_search

Search PharmacoDB for compounds, cell lines, tissues, or genes by name. PharmacoDB integrates can...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_search(
    operation: str,
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search PharmacoDB for compounds, cell lines, tissues, or genes by name. PharmacoDB integrates can...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Text query to search across compounds, cell lines, tissues, and genes. Exampl...
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

    return get_shared_client().run_one_function(
        {
            "name": "PharmacoDB_search",
            "arguments": {"operation": operation, "query": query},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_search"]
