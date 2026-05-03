"""
drugbank_vocab_search

Search the DrugBank vocabulary dataset for drugs by name, ID, synonyms, or other fields using tex...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def drugbank_vocab_search(
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
    Search the DrugBank vocabulary dataset for drugs by name, ID, synonyms, or other fields using tex...

    Parameters
    ----------
    query : str
        Search query string. Can be drug name, synonym, DrugBank ID, or any text to s...
    search_fields : list[str]
        Fields to search in. Available fields: 'DrugBank ID', 'Accession Numbers', 'C...
    case_sensitive : bool
        Whether the search should be case sensitive.
    exact_match : bool
        Whether to perform exact matching instead of substring matching.
    limit : int
        Maximum number of results to return.
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
            "name": "drugbank_vocab_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["drugbank_vocab_search"]
