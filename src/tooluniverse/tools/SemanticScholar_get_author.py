"""
SemanticScholar_get_author

Get detailed profile for a specific author on Semantic Scholar by author ID. Returns name, h-inde...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SemanticScholar_get_author(
    author_id: str,
    fields: Optional[
        str
    ] = "name,hIndex,citationCount,paperCount,affiliations,homepage,papers.title,papers.year,papers.citationCount,papers.paperId",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed profile for a specific author on Semantic Scholar by author ID. Returns name, h-inde...

    Parameters
    ----------
    author_id : str
        Semantic Scholar author ID (e.g., '1741101' for Oren Etzioni). Find using Sem...
    fields : str
        Comma-separated fields: name,hIndex,citationCount,paperCount,affiliations,hom...
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
            "name": "SemanticScholar_get_author",
            "arguments": {"author_id": author_id, "fields": fields},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SemanticScholar_get_author"]
