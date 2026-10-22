"""
HumanMine_search_genes

Search HumanMine specifically for genes by symbol, name, or ID across human, mouse, and rat. Huma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HumanMine_search_genes(
    q: str,
    size: Optional[int] = None,
    start: Optional[int] = 0,
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
    size : int
        Number of results in this page (default 10, max 100)
    start : int
        Zero-based search offset. Continue with metadata.next_start while metadata.ha...
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
        k: v for k, v in {"q": q, "size": size, "start": start}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HumanMine_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HumanMine_search_genes"]
