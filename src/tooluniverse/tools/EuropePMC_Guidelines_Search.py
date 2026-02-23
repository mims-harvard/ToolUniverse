"""
EuropePMC_Guidelines_Search

Search Europe PMC for clinical guidelines and evidence-based recommendations. Europe PMC provides...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_Guidelines_Search(
    query: str,
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Europe PMC for clinical guidelines and evidence-based recommendations. Europe PMC provides...

    Parameters
    ----------
    query : str
        Medical condition, treatment, or clinical topic to search for (e.g., 'diabete...
    limit : int
        Maximum number of guidelines to return (default: 10)
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
            "name": "EuropePMC_Guidelines_Search",
            "arguments": {"query": query, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_Guidelines_Search"]
