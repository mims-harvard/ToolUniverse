"""
USPTO_search_enriched_citations

Search AI-extracted citation data from USPTO office actions. Returns which prior art was cited ag...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USPTO_search_enriched_citations(
    query: str,
    offset: Optional[int] = 0,
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search AI-extracted citation data from USPTO office actions. Returns which prior art was cited ag...

    Parameters
    ----------
    query : str
        Lucene query string. Examples: 'patentApplicationNumber:14966067', 'citationC...
    offset : int
        Start position for pagination (default 0)
    limit : int
        Maximum results to return (default 25)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "query": query,
                "offset": offset,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USPTO_search_enriched_citations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["USPTO_search_enriched_citations"]
