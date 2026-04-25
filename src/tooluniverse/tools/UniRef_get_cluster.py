"""
UniRef_get_cluster

Get detailed information about a UniProt UniRef protein sequence cluster. UniRef clusters group r...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniRef_get_cluster(
    cluster_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a UniProt UniRef protein sequence cluster. UniRef clusters group r...

    Parameters
    ----------
    cluster_id : str
        UniRef cluster ID. Format: UniRefNN_ACCESSION. Examples: 'UniRef90_P04637' (p...
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
        "cluster_id": cluster_id
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniRef_get_cluster",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["UniRef_get_cluster"]
