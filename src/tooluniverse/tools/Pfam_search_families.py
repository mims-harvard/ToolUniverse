"""
Pfam_search_families

Search for Pfam protein family entries by keyword using the InterPro API. Pfam is the authoritati...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pfam_search_families(
    query: str,
    max_results: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for Pfam protein family entries by keyword using the InterPro API. Pfam is the authoritati...

    Parameters
    ----------
    query : str
        Search keyword. Examples: 'kinase', 'zinc finger', 'helicase', 'immunoglobuli...
    max_results : int
        Maximum number of results to return (default 20, max 100).
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
        k: v
        for k, v in {"query": query, "max_results": max_results}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pfam_search_families",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pfam_search_families"]
