"""
Dataverse_search_datasets

Search the Harvard Dataverse repository for research datasets, files, and dataverses. Harvard Dat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dataverse_search_datasets(
    q: str,
    type_: Optional[str | Any] = None,
    per_page: Optional[int | Any] = None,
    start: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Harvard Dataverse repository for research datasets, files, and dataverses. Harvard Dat...

    Parameters
    ----------
    q : str
        Search query string for dataset title, description, or keyword (e.g., 'climat...
    type_ : str | Any
        Filter by type: 'dataset', 'file', or 'dataverse' (default: returns all types)
    per_page : int | Any
        Number of results per page (default 10)
    start : int | Any
        Result offset for pagination (0-based, e.g., 0, 10, 20)
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
            "q": q,
            "type": type_,
            "per_page": per_page,
            "start": start,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Dataverse_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Dataverse_search_datasets"]
