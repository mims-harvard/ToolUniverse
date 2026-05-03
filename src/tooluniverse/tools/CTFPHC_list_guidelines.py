"""
CTFPHC_list_guidelines

List all published guidelines from the Canadian Task Force on Preventive Health Care (CTFPHC). Fe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTFPHC_list_guidelines(
    limit: Optional[int] = 30,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all published guidelines from the Canadian Task Force on Preventive Health Care (CTFPHC). Fe...

    Parameters
    ----------
    limit : int
        Maximum number of guidelines to return (default: 30)
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
    _args = {k: v for k, v in {"limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CTFPHC_list_guidelines",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTFPHC_list_guidelines"]
