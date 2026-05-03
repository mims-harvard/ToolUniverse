"""
NDEx_get_network

Get the full content of a biological network from NDEx including all nodes (proteins/genes) and e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NDEx_get_network(
    uuid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full content of a biological network from NDEx including all nodes (proteins/genes) and e...

    Parameters
    ----------
    uuid : str
        NDEx network UUID. Example: '34eec19d-ab5a-11ea-aaef-0ac135e8bacf' (BRCA1 int...
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
    _args = {k: v for k, v in {"uuid": uuid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NDEx_get_network",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NDEx_get_network"]
