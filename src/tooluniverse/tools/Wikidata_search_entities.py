"""
Wikidata_search_entities

Search Wikidata for entities (items, properties, or lexemes) by label or description using the Me...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Wikidata_search_entities(
    search: str,
    language: Optional[str | Any] = None,
    type_: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Wikidata for entities (items, properties, or lexemes) by label or description using the Me...

    Parameters
    ----------
    search : str
        Search term to find Wikidata entities. Examples: 'CRISPR', 'Albert Einstein',...
    language : str | Any
        Language code for search and results. Default: 'en'. Examples: 'fr', 'de', 'z...
    type_ : str | Any
        Entity type to search. Values: 'item' (Q-numbers, default), 'property' (P-num...
    limit : int | Any
        Number of results to return (default 7, max 50)
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
            "name": "Wikidata_search_entities",
            "arguments": {
                "search": search,
                "language": language,
                "type": type_,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Wikidata_search_entities"]
