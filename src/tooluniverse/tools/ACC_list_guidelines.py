"""
ACC_list_guidelines

List recent American College of Cardiology (ACC) clinical practice guidelines. Returns ACC-author...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ACC_list_guidelines(
    limit: Optional[int] = 10,
    year_from: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List recent American College of Cardiology (ACC) clinical practice guidelines. Returns ACC-author...

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

    return get_shared_client().run_one_function(
        {
            "name": "ACC_list_guidelines",
            "arguments": {"limit": limit, "year_from": year_from},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ACC_list_guidelines"]
