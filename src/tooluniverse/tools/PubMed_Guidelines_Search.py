"""
PubMed_Guidelines_Search

Search PubMed for peer-reviewed clinical practice guidelines using NCBI E-utilities. Filters resu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMed_Guidelines_Search(
    query: str,
    limit: int,
    api_key: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search PubMed for peer-reviewed clinical practice guidelines using NCBI E-utilities. Filters resu...

    Parameters
    ----------
    query : str
        Medical condition, treatment, or clinical topic to search for (e.g., 'diabete...
    limit : int
        Maximum number of guidelines to return (default: 10)
    api_key : str | Any
        Optional NCBI API key for higher rate limits. Get your free key at https://ww...
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
            "name": "PubMed_Guidelines_Search",
            "arguments": {"query": query, "limit": limit, "api_key": api_key},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMed_Guidelines_Search"]
