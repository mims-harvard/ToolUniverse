"""
Bioconductor_search_packages

Search Bioconductor bioinformatics R packages by keyword, topic, or analysis type. Bioconductor p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bioconductor_search_packages(
    q: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Bioconductor bioinformatics R packages by keyword, topic, or analysis type. Bioconductor p...

    Parameters
    ----------
    q : str
        Search query for Bioconductor packages. Can be a keyword, analysis type, or t...
    limit : int | Any
        Maximum number of results to return (default: 10, max: 100)
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
        {"name": "Bioconductor_search_packages", "arguments": {"q": q, "limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bioconductor_search_packages"]
