"""
intact_get_interactor

Get detailed information about a specific interactor from IntAct database by IntAct identifier (e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def intact_get_interactor(
    identifier: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific interactor from IntAct database by IntAct identifier (e...

    Parameters
    ----------
    identifier : str
        IntAct identifier (e.g., 'EBI-1004115') or UniProt ID (e.g., 'P04637') or gen...
    format : str
        Response format
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
        for k, v in {"identifier": identifier, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "intact_get_interactor",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["intact_get_interactor"]
