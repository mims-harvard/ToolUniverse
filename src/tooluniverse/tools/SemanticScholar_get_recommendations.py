"""
SemanticScholar_get_recommendations

Get paper recommendations from Semantic Scholar for a given paper. Returns papers similar to or r...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SemanticScholar_get_recommendations(
    paper_id: str,
    limit: Optional[int] = 10,
    fields: Optional[str] = "title,year,citationCount,abstract,authors,externalIds",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get paper recommendations from Semantic Scholar for a given paper. Returns papers similar to or r...

    Parameters
    ----------
    paper_id : str
        Semantic Scholar paper ID (40-char hex, e.g., '68d962effe5520777791bd6ec8ffa4...
    limit : int
        Number of recommendations to return (default 10, max 500)
    fields : str
        Comma-separated fields for recommended papers: title,year,citationCount,abstr...
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
        for k, v in {"paper_id": paper_id, "limit": limit, "fields": fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SemanticScholar_get_recommendations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SemanticScholar_get_recommendations"]
