"""
SCP_list_studies

List the public Single Cell Portal study catalog (1000+ studies), sorted by cell count descending...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCP_list_studies(
    keyword: Optional[str] = None,
    min_cells: Optional[int] = None,
    limit: Optional[int] = None,
    description_chars: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the public Single Cell Portal study catalog (1000+ studies), sorted by cell count descending...

    Parameters
    ----------
    keyword : str
        Optional case-insensitive filter matched against study title and description,...
    min_cells : int
        Only return studies with at least this many cells, e.g. 100000.
    limit : int
        Maximum studies to return (default 20, max 100).
    description_chars : int
        Truncate each description to this many characters (default 300). Set 0 to omi...
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
            "keyword": keyword,
            "min_cells": min_cells,
            "limit": limit,
            "description_chars": description_chars,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCP_list_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCP_list_studies"]
