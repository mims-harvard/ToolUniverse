"""
SemanticScholar_get_author_papers

List an author's full publication bibliography from Semantic Scholar, one row per paper, with per...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SemanticScholar_get_author_papers(
    author_id: str,
    fields: Optional[
        str
    ] = "paperId,title,year,citationCount,venue,externalIds,authors,openAccessPdf",
    limit: Optional[int] = 50,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List an author's full publication bibliography from Semantic Scholar, one row per paper, with per...

    Parameters
    ----------
    author_id : str
        Semantic Scholar author ID (e.g., '1741101' for Oren Etzioni). Find using Sem...
    fields : str
        Comma-separated per-paper fields. Available: paperId, title, year, citationCo...
    limit : int
        Maximum number of papers to return (default 50, max 1000).
    offset : int
        Pagination offset into the author's paper list (default 0).
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
        for k, v in {
            "author_id": author_id,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SemanticScholar_get_author_papers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SemanticScholar_get_author_papers"]
