"""
MyDisease_search_diseases

Search for diseases by keyword in MyDisease.info, a BioThings aggregator combining data from MOND...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyDisease_search_diseases(
    query: str,
    size: Optional[int] = 10,
    fields: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for diseases by keyword in MyDisease.info, a BioThings aggregator combining data from MOND...

    Parameters
    ----------
    query : str
        Search query. Can be disease name (e.g., 'breast cancer', 'melanoma', 'diabet...
    size : int
        Maximum number of results to return (default 10, max 100).
    fields : str
        Comma-separated list of fields to include in results. Default: 'mondo.label,d...
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
            "name": "MyDisease_search_diseases",
            "arguments": {"query": query, "size": size, "fields": fields},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyDisease_search_diseases"]
