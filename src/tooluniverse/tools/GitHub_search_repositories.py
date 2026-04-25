"""
GitHub_search_repositories

Search GitHub public repositories using GitHub's search API. Returns repository metadata includin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GitHub_search_repositories(
    q: str,
    sort: Optional[str | Any] = None,
    order: Optional[str | Any] = None,
    per_page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search GitHub public repositories using GitHub's search API. Returns repository metadata includin...

    Parameters
    ----------
    q : str
        Search query with optional qualifiers. Examples: 'bioinformatics language:pyt...
    sort : str | Any
        Sort by: 'stars', 'forks', 'help-wanted-issues', 'updated'. Default: best match.
    order : str | Any
        Sort direction: 'desc' (default) or 'asc'
    per_page : int | Any
        Results per page (default 30, max 100)
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
    _args = {k: v for k, v in {
        "q": q,
                "sort": sort,
                "order": order,
                "per_page": per_page
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GitHub_search_repositories",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["GitHub_search_repositories"]
