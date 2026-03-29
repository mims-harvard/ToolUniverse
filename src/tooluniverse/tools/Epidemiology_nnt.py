"""
Epidemiology_nnt

Calculate Number Needed to Treat (NNT) or Number Needed to Harm (NNH), Absolute Risk Reduction (A...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Epidemiology_nnt(
    operation: str,
    control_rate: float,
    treatment_rate: float,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate Number Needed to Treat (NNT) or Number Needed to Harm (NNH), Absolute Risk Reduction (A...

    Parameters
    ----------
    operation : str
        Operation type
    control_rate : float
        Event rate in the control group [0, 1]
    treatment_rate : float
        Event rate in the treatment group [0, 1]
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
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Epidemiology_nnt",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Epidemiology_nnt"]
