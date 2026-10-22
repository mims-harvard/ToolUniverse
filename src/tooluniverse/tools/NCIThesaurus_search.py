"""
NCIThesaurus_search

Search the NCI Thesaurus (NCIt) for biomedical concepts with explicit match semantics and offset ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCIThesaurus_search(
    term: str,
    page_size: Optional[int] = 10,
    offset: Optional[int] = 0,
    match_type: Optional[str] = "match",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the NCI Thesaurus (NCIt) for biomedical concepts with explicit match semantics and offset ...

    Parameters
    ----------
    term : str
        Search term for NCI concepts. Examples: 'melanoma', 'breast cancer', 'imatini...
    page_size : int
        Number of results to return per page (default 10, range 1-100).
    offset : int
        Zero-based start index sent as the official EVS fromRecord parameter. Continu...
    match_type : str
        Official EVS match behavior. 'match' is the compatibility default; 'contains'...
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
            "term": term,
            "page_size": page_size,
            "offset": offset,
            "match_type": match_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCIThesaurus_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCIThesaurus_search"]
