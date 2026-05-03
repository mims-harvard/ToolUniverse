"""
EMPIAR_search_entries

Search the EMPIAR (Electron Microscopy Public Image Archive) for raw EM image datasets by keyword...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EMPIAR_search_entries(
    query: str,
    page_size: Optional[int] = 10,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the EMPIAR (Electron Microscopy Public Image Archive) for raw EM image datasets by keyword...

    Parameters
    ----------
    query : str
        Search query keyword (e.g., 'ribosome', 'membrane protein', 'SARS-CoV-2')
    page_size : int
        Number of results to return (default: 10, max: 100)
    start : int
        Starting offset for pagination (default: 0)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"query": query, "page_size": page_size, "start": start}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EMPIAR_search_entries",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EMPIAR_search_entries"]
