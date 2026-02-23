"""
UniProt_search_proteomes

Search the UniProt Proteome database for complete sets of proteins expressed by organisms. Proteo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_search_proteomes(
    query: str,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the UniProt Proteome database for complete sets of proteins expressed by organisms. Proteo...

    Parameters
    ----------
    query : str
        Search query using UniProt query syntax. Examples: 'organism_name:human', 'or...
    size : int
        Number of results to return (default 10, max 500)
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
            "name": "UniProt_search_proteomes",
            "arguments": {"query": query, "size": size},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_search_proteomes"]
