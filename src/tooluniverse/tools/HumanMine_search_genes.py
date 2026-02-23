"""
HumanMine_search_genes

Search HumanMine specifically for genes by symbol, name, or ID across human, mouse, and rat. Huma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HumanMine_search_genes(
    q: str,
    size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search HumanMine specifically for genes by symbol, name, or ID across human, mouse, and rat. Huma...

    Parameters
    ----------
    q : str
        Gene search query: gene symbol (e.g., 'EGFR', 'TP53'), gene name (e.g., 'tumo...
    size : int | Any
        Maximum number of results to return (default 10, max 100)
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
        {"name": "HumanMine_search_genes", "arguments": {"q": q, "size": size}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HumanMine_search_genes"]
