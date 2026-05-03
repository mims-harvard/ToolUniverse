"""
DoseResponse_fit_curve

Nonlinear regression of paired concentration-response measurements to the Hill sigmoidal (4PL) mo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DoseResponse_fit_curve(
    operation: str,
    concentrations: list[Any],
    responses: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Nonlinear regression of paired concentration-response measurements to the Hill sigmoidal (4PL) mo...

    Parameters
    ----------
    operation : str
        Operation type
    concentrations : list[Any]
        Drug concentrations (must be positive, e.g., [0.001, 0.01, 0.1, 1, 10, 100] i...
    responses : list[Any]
        Observed responses at each concentration (e.g., % inhibition [0-100] or viabi...
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
        for k, v in {
            "operation": operation,
            "concentrations": concentrations,
            "responses": responses,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DoseResponse_fit_curve",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DoseResponse_fit_curve"]
