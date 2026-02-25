"""
CellPainting_search_screens

List available Cell Painting screens/studies in the Image Data Resource (IDR). Returns screen nam...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellPainting_search_screens(
    operation: str,
    query: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List available Cell Painting screens/studies in the Image Data Resource (IDR). Returns screen nam...

    Parameters
    ----------
    operation : str
        Operation type
    query : str | Any
        Optional keyword to filter screens by name or description (e.g., 'JUMP', 'U2O...
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

    return get_shared_client().run_one_function(
        {
            "name": "CellPainting_search_screens",
            "arguments": {"operation": operation, "query": query},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CellPainting_search_screens"]
