"""
openalex_search_institutions

Search OpenAlex institutions via the /institutions endpoint. Use this to discover Institution IDs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def openalex_search_institutions(
    search: str,
    per_page: Optional[int] = 5,
    page: Optional[int] = 1,
    mailto: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Search OpenAlex institutions via the /institutions endpoint. Use this to discover Institution IDs...

    Parameters
    ----------
    search : str
        Institution name search query. Example: "Harvard University".
    per_page : int
        Results per page (OpenAlex max 200).
    page : int
        Page number (1-indexed).
    mailto : str
        Optional contact email for OpenAlex polite pool.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "search": search,
            "per_page": per_page,
            "page": page,
            "mailto": mailto,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "openalex_search_institutions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["openalex_search_institutions"]
