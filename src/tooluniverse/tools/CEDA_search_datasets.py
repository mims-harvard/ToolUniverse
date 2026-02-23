"""
CEDA_search_datasets

Search the CEDA (Centre for Environmental Data Analysis) data catalogue for UK and global environ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CEDA_search_datasets(
    q: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the CEDA (Centre for Environmental Data Analysis) data catalogue for UK and global environ...

    Parameters
    ----------
    q : str | Any
        Search query for datasets. Examples: 'climate model', 'sea surface temperatur...
    limit : int | Any
        Number of results to return (default 10, max 100)
    offset : int | Any
        Offset for pagination
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
            "name": "CEDA_search_datasets",
            "arguments": {"q": q, "limit": limit, "offset": offset},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CEDA_search_datasets"]
