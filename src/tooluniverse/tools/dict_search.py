"""
dict_search

Search the DICTrank dataset for drug-induced cardiotoxicity (DICT) risk information by trade name...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dict_search(
    query: str,
    search_fields: list[str],
    case_sensitive: bool,
    exact_match: bool,
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the DICTrank dataset for drug-induced cardiotoxicity (DICT) risk information by trade name...

    Parameters
    ----------
    query : str
        Free-text query (e.g. 'ZYPREXA', 'Olanzapine').
    search_fields : list[str]
        Columns to search. Choose from: 'Trade Name', 'Generic/Proper Name(s)', 'Acti...
    case_sensitive : bool
        Match text with exact case if true.
    exact_match : bool
        Field value must equal query exactly if true; otherwise substring match.
    limit : int
        Maximum number of rows to return.
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "search_fields": search_fields,
            "case_sensitive": case_sensitive,
            "exact_match": exact_match,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "dict_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dict_search"]
