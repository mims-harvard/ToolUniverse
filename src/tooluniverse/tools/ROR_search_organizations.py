"""
ROR_search_organizations

Search Research Organization Registry (ROR) v2 with explicit page pagination and exact total meta...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ROR_search_organizations(
    query: str,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Research Organization Registry (ROR) v2 with explicit page pagination and exact total meta...

    Parameters
    ----------
    query : str
        Search query for organization name, acronym, or keyword (e.g., 'MIT', 'Harvar...
    page : int
        One-based ROR result page. Each page contains up to 20 organizations. Continu...
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
    _args = {k: v for k, v in {"query": query, "page": page}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ROR_search_organizations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ROR_search_organizations"]
