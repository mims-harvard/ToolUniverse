"""
MaveDB_get_score_set

Get detailed information about a specific MaveDB score set by its URN identifier. Returns the tar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MaveDB_get_score_set(
    urn: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific MaveDB score set by its URN identifier. Returns the tar...

    Parameters
    ----------
    urn : str
        MaveDB score set URN (e.g., 'urn:mavedb:00000001-a-1'). Obtain URNs from Mave...
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
    _args = {k: v for k, v in {"urn": urn}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MaveDB_get_score_set",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MaveDB_get_score_set"]
