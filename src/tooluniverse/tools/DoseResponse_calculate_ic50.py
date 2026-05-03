"""
DoseResponse_calculate_ic50

Determine the half-maximal inhibitory or effective concentration (IC50/EC50) from paired concentr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DoseResponse_calculate_ic50(
    operation: str,
    concentrations: list[Any],
    responses: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Determine the half-maximal inhibitory or effective concentration (IC50/EC50) from paired concentr...

    Parameters
    ----------
    operation : str
        Operation type
    concentrations : list[Any]
        Drug concentrations (positive values, e.g., in µM or nM)
    responses : list[Any]
        Percent inhibition or effect values at each concentration
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
            "name": "DoseResponse_calculate_ic50",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DoseResponse_calculate_ic50"]
