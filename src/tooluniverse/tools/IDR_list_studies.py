"""
IDR_list_studies

List imaging studies (projects) from the Image Data Resource (IDR), the public repository for ref...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_list_studies(
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List imaging studies (projects) from the Image Data Resource (IDR), the public repository for ref...

    Parameters
    ----------
    limit : int | Any
        Maximum number of studies to return (default 25, max 1000)
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
        {"name": "IDR_list_studies", "arguments": {"limit": limit, "offset": offset}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDR_list_studies"]
