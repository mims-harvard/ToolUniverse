"""
CTFPHC_list_guidelines

List the current official Canadian Task Force on Preventive Health Care published-guideline index...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTFPHC_list_guidelines(
    limit: Optional[int] = 30,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the current official Canadian Task Force on Preventive Health Care published-guideline index...

    Parameters
    ----------
    limit : int
        Maximum number of guidelines to return (default: 30)
    offset : int
        Zero-based offset in the official guideline index. Continue with each item's ...
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
        k: v for k, v in {"limit": limit, "offset": offset}.items() if v is not None
    }
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
