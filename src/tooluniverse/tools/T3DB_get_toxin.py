"""
T3DB_get_toxin

Get detailed toxin information from the Toxin and Toxin-Target Database (T3DB) by T3DB ID. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def T3DB_get_toxin(
    toxin_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed toxin information from the Toxin and Toxin-Target Database (T3DB) by T3DB ID. Return...

    Parameters
    ----------
    toxin_id : str
        T3DB toxin ID (e.g., 'T3D0001' for Arsenic, 'T3D0002' for Lead). Numeric-only...
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
    _args = {k: v for k, v in {"toxin_id": toxin_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "T3DB_get_toxin",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["T3DB_get_toxin"]
