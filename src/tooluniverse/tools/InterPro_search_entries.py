"""
InterPro_search_entries

Search InterPro entries (domains, families, sites) by keyword. Returns matching InterPro entries ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_search_entries(
    query: str,
    entry_type: Optional[str] = None,
    page_size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search InterPro entries (domains, families, sites) by keyword. Returns matching InterPro entries ...

    Parameters
    ----------
    query : str
        Search keyword. Examples: 'zinc finger' (466 entries), 'kinase', 'immunoglobu...
    entry_type : str
        Filter by entry type. Options: 'domain', 'family', 'homologous_superfamily', ...
    page_size : int
        Number of results to return (1-50, default 20).
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
            "name": "InterPro_search_entries",
            "arguments": {
                "query": query,
                "entry_type": entry_type,
                "page_size": page_size,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_search_entries"]
