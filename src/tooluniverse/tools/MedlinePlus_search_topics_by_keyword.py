"""
MedlinePlus_search_topics_by_keyword

Search for relevant information in MedlinePlus Web Service by keyword across health topics or oth...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedlinePlus_search_topics_by_keyword(
    term: str,
    db: str,
    rettype: Optional[str] = "topic",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for relevant information in MedlinePlus Web Service by keyword across health topics or oth...

    Parameters
    ----------
    term : str
        Search keyword, e.g., "diabetes", needs to be URL encoded before passing.
    db : str
        Specify the database to search, e.g., healthTopics (English health topics), h...
    rettype : str
        Result return format, options: brief (concise information, default), topic (d...
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
        for k, v in {"term": term, "db": db, "rettype": rettype}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MedlinePlus_search_topics_by_keyword",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedlinePlus_search_topics_by_keyword"]
