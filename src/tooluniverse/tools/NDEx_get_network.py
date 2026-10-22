"""
NDEx_get_network

Get a recoverable page of biological network content from NDEx, including nodes (proteins/genes) ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NDEx_get_network(
    uuid: str,
    node_limit: Optional[int] = 200,
    node_offset: Optional[int] = 0,
    edge_limit: Optional[int] = 500,
    edge_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a recoverable page of biological network content from NDEx, including nodes (proteins/genes) ...

    Parameters
    ----------
    uuid : str
        NDEx network UUID. Example: '34eec19d-ab5a-11ea-aaef-0ac135e8bacf' (BRCA1 int...
    node_limit : int
        Maximum nodes to return on this page.
    node_offset : int
        Zero-based node offset. Follow next_node_offset for the next node page.
    edge_limit : int
        Maximum edges to return on this page.
    edge_offset : int
        Zero-based edge offset. Follow next_edge_offset for the next edge page.
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
            "uuid": uuid,
            "node_limit": node_limit,
            "node_offset": node_offset,
            "edge_limit": edge_limit,
            "edge_offset": edge_offset,
        }.items()
        if v is not None
    }
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
