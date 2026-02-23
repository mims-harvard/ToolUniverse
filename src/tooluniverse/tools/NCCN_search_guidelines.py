"""
NCCN_search_guidelines

Search NCCN (National Comprehensive Cancer Network) guidelines and publications via PubMed. Searc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCCN_search_guidelines(
    query: str,
    limit: Optional[int] = 5,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NCCN (National Comprehensive Cancer Network) guidelines and publications via PubMed. Searc...

    Parameters
    ----------
    query : str
        Search topic (e.g., 'breast cancer treatment', 'non-small cell lung cancer', ...
    limit : int
        Maximum number of results to return (default: 5)
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
            "name": "NCCN_search_guidelines",
            "arguments": {"query": query, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCCN_search_guidelines"]
