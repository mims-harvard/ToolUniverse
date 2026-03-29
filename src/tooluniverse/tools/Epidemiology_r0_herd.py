"""
Epidemiology_r0_herd

Compute herd immunity threshold and effective reproduction number from R0 and vaccine efficacy. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Epidemiology_r0_herd(
    operation: str,
    R0: float,
    VE: Optional[float] = None,
    coverage: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compute herd immunity threshold and effective reproduction number from R0 and vaccine efficacy. R...

    Parameters
    ----------
    operation : str
        Operation type
    R0 : float
        Basic reproduction number (must be > 1)
    VE : float
        Vaccine efficacy as fraction (0, 1], default 1.0 (perfect vaccine)
    coverage : float
        Optional vaccination coverage fraction [0, 1] to evaluate Re at
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
        for k, v in {
            "operation": operation,
            "R0": R0,
            "VE": VE,
            "coverage": coverage,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Epidemiology_r0_herd",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Epidemiology_r0_herd"]
