"""
AHA_list_guidelines

List recent American Heart Association (AHA) clinical practice guidelines. Returns AHA-authored g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AHA_list_guidelines(
    limit: Optional[int] = 10,
    year_from: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List recent American Heart Association (AHA) clinical practice guidelines. Returns AHA-authored g...

    Parameters
    ----------
    limit : int
        Maximum number of guidelines to return (default: 10)
    year_from : int | Any
        Filter to guidelines published from this year onward (e.g., 2020). Null for n...
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
        for k, v in {"limit": limit, "year_from": year_from}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AHA_list_guidelines",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AHA_list_guidelines"]
