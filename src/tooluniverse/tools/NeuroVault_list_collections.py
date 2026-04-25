"""
NeuroVault_list_collections

List and browse neuroimaging statistical map collections from NeuroVault. Returns collections of ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroVault_list_collections(
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    format: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List and browse neuroimaging statistical map collections from NeuroVault. Returns collections of ...

    Parameters
    ----------
    limit : int | Any
        Maximum number of collections to return per page (default 10, max 100). Examp...
    offset : int | Any
        Number of collections to skip for pagination (default 0). Example: 20 to get ...
    format : str | Any
        Response format. Must be 'json'. Default: 'json'
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
    _args = {k: v for k, v in {
        "limit": limit,
                "offset": offset,
                "format": format
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NeuroVault_list_collections",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["NeuroVault_list_collections"]
