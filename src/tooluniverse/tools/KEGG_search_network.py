"""
KEGG_search_network

Search the KEGG NETWORK database for signaling pathway networks by gene or keyword. KEGG NETWORK ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_search_network(
    keyword: str,
    max_results: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the KEGG NETWORK database for signaling pathway networks by gene or keyword. KEGG NETWORK ...

    Parameters
    ----------
    keyword : str
        Search keyword for network/pathway name or gene (e.g., 'EGFR', 'RAS', 'p53', ...
    max_results : int
        Maximum number of results (default: 25).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"keyword": keyword, "max_results": max_results}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_search_network",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_search_network"]
