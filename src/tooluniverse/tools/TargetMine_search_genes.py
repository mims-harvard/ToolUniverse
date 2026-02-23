"""
TargetMine_search_genes

Search TargetMine specifically for genes relevant to drug target discovery. This convenience wrap...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TargetMine_search_genes(
    q: str,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search TargetMine specifically for genes relevant to drug target discovery. This convenience wrap...

    Parameters
    ----------
    q : str
        Gene search query: gene symbol (e.g., 'TP53', 'EGFR', 'BRCA1'), Entrez Gene I...
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
        {"name": "TargetMine_search_genes", "arguments": {"q": q, "size": size}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TargetMine_search_genes"]
