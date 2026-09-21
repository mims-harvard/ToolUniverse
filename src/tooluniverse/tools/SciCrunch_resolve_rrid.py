"""
SciCrunch_resolve_rrid

Resolve any Research Resource Identifier (RRID) via SciCrunch's registry: software/tools (SCR_ pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SciCrunch_resolve_rrid(
    rrid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve any Research Resource Identifier (RRID) via SciCrunch's registry: software/tools (SCR_ pr...

    Parameters
    ----------
    rrid : str
        RRID with or without prefix, e.g. 'SCR_002526' or 'RRID:SCR_002526'.
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
    _args = {k: v for k, v in {"rrid": rrid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SciCrunch_resolve_rrid",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SciCrunch_resolve_rrid"]
