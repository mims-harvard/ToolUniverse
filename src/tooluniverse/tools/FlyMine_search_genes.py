"""
FlyMine_search_genes

Search FlyMine specifically for Drosophila genes. This is a convenience wrapper that filters resu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FlyMine_search_genes(
    q: str,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FlyMine specifically for Drosophila genes. This is a convenience wrapper that filters resu...

    Parameters
    ----------
    q : str
        Gene search query: gene symbol (e.g., 'dpp', 'Notch', 'wg', 'hh'), FlyBase ID...
    size : int
        Number of results to return (default: 10).
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
        {"name": "FlyMine_search_genes", "arguments": {"q": q, "size": size}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FlyMine_search_genes"]
