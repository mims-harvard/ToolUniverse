"""
pubmed_unified_search_mcp

Main search entry point - auto multi-source search across PubMed, Europe PMC, CORE (200M+ papers)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_unified_search_mcp(
    query: str,
    limit: Optional[int] = 10,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    ranking: Optional[str] = "balanced",
    sources: Optional[list[str]] = None,
    include_oa_links: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Main search entry point - auto multi-source search across PubMed, Europe PMC, CORE (200M+ papers)...

    Parameters
    ----------
    query : str
        Search query (natural language or PubMed syntax)
    limit : int

    min_year : int

    max_year : int

    ranking : str

    sources : list[str]
        Sources to search: pubmed, europe_pmc, core, openalex
    include_oa_links : bool

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
            "name": "pubmed_unified_search_mcp",
            "arguments": {
                "query": query,
                "limit": limit,
                "min_year": min_year,
                "max_year": max_year,
                "ranking": ranking,
                "sources": sources,
                "include_oa_links": include_oa_links,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_unified_search_mcp"]
