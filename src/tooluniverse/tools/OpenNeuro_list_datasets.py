"""
OpenNeuro_list_datasets

List publicly available neuroimaging datasets on OpenNeuro. OpenNeuro hosts 1000+ BIDS-formatted ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenNeuro_list_datasets(
    first: Optional[int | Any] = None,
    after: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List publicly available neuroimaging datasets on OpenNeuro. OpenNeuro hosts 1000+ BIDS-formatted ...

    Parameters
    ----------
    first : int | Any
        Number of datasets to return (default 10, max 25)
    after : str | Any
        Cursor for pagination - use endCursor from previous response
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
            "name": "OpenNeuro_list_datasets",
            "arguments": {"first": first, "after": after},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenNeuro_list_datasets"]
