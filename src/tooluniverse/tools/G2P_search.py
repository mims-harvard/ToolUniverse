"""
G2P_search

Search the Gene2Phenotype (G2P) database for gene-disease associations curated by clinical geneti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def G2P_search(
    query: str,
    page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Gene2Phenotype (G2P) database for gene-disease associations curated by clinical geneti...

    Parameters
    ----------
    query : str
        Search query - gene symbol (e.g., 'BRCA1', 'TP53') or disease name (e.g., 'ep...
    page : int | Any
        Page number for pagination (default 1)
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
        {"name": "G2P_search", "arguments": {"query": query, "page": page}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["G2P_search"]
