"""
INDRA_get_statement_by_hash

Get a specific INDRA statement by its hash with full evidence details. Use statement hashes retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def INDRA_get_statement_by_hash(
    hash: str,
    operation: Optional[str] = None,
    ev_limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get a specific INDRA statement by its hash with full evidence details. Use statement hashes retur...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_statement_by_hash)
    hash : str
        Statement hash from INDRA_get_statements results
    ev_limit : int
        Maximum evidence items to return (default: 10)
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
    _args = {
        k: v
        for k, v in {"operation": operation, "hash": hash, "ev_limit": ev_limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "INDRA_get_statement_by_hash",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["INDRA_get_statement_by_hash"]
