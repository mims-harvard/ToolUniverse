"""
BioThings_query

Search any BioThings-hosted API with an Elasticsearch-style query. Use '*' to match everything, a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioThings_query(
    api: str,
    q: str,
    size: Optional[int] = None,
    skip: Optional[int] = None,
    fields: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search any BioThings-hosted API with an Elasticsearch-style query. Use '*' to match everything, a...

    Parameters
    ----------
    api : str
        API slug, e.g. 'ddinter', 'repodb', 'semmeddb'. See BioThings_list_apis.
    q : str
        Query string. '*' for all, a bare term for full-text, or 'field:value' for fi...
    size : int
        Maximum records to return (default 10, max 100).
    skip : int
        Number of records to skip, for paging through large result sets.
    fields : str
        Comma-separated fields to return, e.g. 'subject,object,predicate'. Omit for all.
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
            "api": api,
            "q": q,
            "size": size,
            "skip": skip,
            "fields": fields,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioThings_query",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioThings_query"]
