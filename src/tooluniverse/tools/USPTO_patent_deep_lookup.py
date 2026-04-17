"""
USPTO_patent_deep_lookup

Analyze multiple US patents in one call. Provide a list of patent numbers OR a search query, and ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USPTO_patent_deep_lookup(
    patent_numbers: Optional[list[str]] = None,
    search_query: Optional[str] = None,
    include: Optional[list[str]] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Analyze multiple US patents in one call. Provide a list of patent numbers OR a search query, and ...

    Parameters
    ----------
    patent_numbers : list[str]
        List of patent numbers in any format. Provide this OR search_query.
    search_query : str
        ODP search query to find patents (e.g., 'applicationMetaData.firstApplicantNa...
    include : list[str]
        Analyses to run: metadata, assignment, claims, transactions, enriched_citatio...
    limit : int
        Maximum patents to analyze (default 10, max 50)
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
    if include is None:
        include = ['metadata']
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "patent_numbers": patent_numbers,
                "search_query": search_query,
                "include": include,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USPTO_patent_deep_lookup",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["USPTO_patent_deep_lookup"]
