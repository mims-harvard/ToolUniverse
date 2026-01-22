"""
pubmed_search_clinvar_mcp

Search ClinVar for clinical variant records.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_search_clinvar_mcp(
    query: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ClinVar for clinical variant records.

    Parameters
    ----------
    query : str
        Variant or gene name
    limit : int

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
            "name": "pubmed_search_clinvar_mcp",
            "arguments": {"query": query, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_search_clinvar_mcp"]
