"""
Wikidata_search_entities

Search Wikidata entities with explicit continuation pagination. Continue with metadata.next_conti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Wikidata_search_entities(
    search: str,
    language: Optional[str] = "en",
    type_: Optional[str] = None,
    limit: Optional[int] = 7,
    continue_: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Wikidata entities with explicit continuation pagination. Continue with metadata.next_conti...

    Parameters
    ----------
    search : str
        Search term to find Wikidata entities. Examples: 'CRISPR', 'Albert Einstein',...
    language : str
        Language code for search and results. Default: 'en'. Examples: 'fr', 'de', 'z...
    type_ : str
        Entity type to search. Values: 'item' (Q-numbers, default), 'property' (P-num...
    limit : int
        Results per page (default 7, max 50)
    continue_ : int
        Continuation offset from the prior response's metadata.next_continue. Use 0 f...
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
            "search": search,
            "language": language,
            "type": type_,
            "limit": limit,
            "continue": continue_,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Wikidata_search_entities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Wikidata_search_entities"]
