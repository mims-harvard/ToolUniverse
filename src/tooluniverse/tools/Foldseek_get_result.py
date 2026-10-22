"""
Foldseek_get_result

Get a recoverable offset page from a previously submitted Foldseek ticket. Completed jobs return ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Foldseek_get_result(
    ticket_id: str,
    max_results: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a recoverable offset page from a previously submitted Foldseek ticket. Completed jobs return ...

    Parameters
    ----------
    ticket_id : str
        Foldseek job ticket ID returned from a previous search submission.
    max_results : int
        Maximum number of results to return (default 10, max 50).
    offset : int
        Zero-based offset in the complete ranked hit list. Continue with data.next_of...
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
            "ticket_id": ticket_id,
            "max_results": max_results,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Foldseek_get_result",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Foldseek_get_result"]
