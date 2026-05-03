"""
UniProt_get_uniref_cluster

Get UniRef cluster information by cluster ID. UniRef clusters group proteins that share 100% (Uni...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_get_uniref_cluster(
    cluster_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get UniRef cluster information by cluster ID. UniRef clusters group proteins that share 100% (Uni...

    Parameters
    ----------
    cluster_id : str
        UniRef cluster ID (e.g., 'UniRef50_P04637', 'UniRef90_P04637', 'UniRef100_P04...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"cluster_id": cluster_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProt_get_uniref_cluster",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_get_uniref_cluster"]
