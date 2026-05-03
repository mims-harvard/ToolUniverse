"""
NASASBDB_get_body

Get physical and orbital data for an asteroid, comet, or small solar system body from NASA's Smal...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASASBDB_get_body(
    sstr: str,
    phys_par: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get physical and orbital data for an asteroid, comet, or small solar system body from NASA's Smal...

    Parameters
    ----------
    sstr : str
        Small body identifier: name, number, or designation. Examples: 'Ceres' (1 Cer...
    phys_par : str | Any
        Whether to include physical parameters: 'true' (default) or 'false'
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
        k: v for k, v in {"sstr": sstr, "phys-par": phys_par}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NASASBDB_get_body",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASASBDB_get_body"]
