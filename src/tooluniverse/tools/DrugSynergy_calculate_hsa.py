"""
DrugSynergy_calculate_hsa

Calculate Highest Single Agent (HSA) synergy score for drug combinations across dose points. HSA ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugSynergy_calculate_hsa(
    operation: str,
    effects_a: list[Any],
    effects_b: list[Any],
    effects_combo: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate Highest Single Agent (HSA) synergy score for drug combinations across dose points. HSA ...

    Parameters
    ----------
    operation : str
        Operation type
    effects_a : list[Any]
        Array of drug A inhibition effects at each dose point (0-1 or 0-100)
    effects_b : list[Any]
        Array of drug B inhibition effects at each dose point (same length as effects_a)
    effects_combo : list[Any]
        Array of combination inhibition effects at each dose point (same length as ef...
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
            "effects_a": effects_a,
            "effects_b": effects_b,
            "effects_combo": effects_combo,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DrugSynergy_calculate_hsa",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugSynergy_calculate_hsa"]
