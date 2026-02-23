"""
ORCID_search_researchers

Search the ORCID registry for researchers by name, affiliation, or keyword. ORCID provides persis...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ORCID_search_researchers(
    q: str,
    rows: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the ORCID registry for researchers by name, affiliation, or keyword. ORCID provides persis...

    Parameters
    ----------
    q : str
        Search query using Lucene syntax. Examples: 'family-name:doudna AND given-nam...
    rows : int
        Number of results to return (default 10, max 200)
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
        {"name": "ORCID_search_researchers", "arguments": {"q": q, "rows": rows}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ORCID_search_researchers"]
