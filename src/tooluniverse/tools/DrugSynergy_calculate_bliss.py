"""
DrugSynergy_calculate_bliss

Calculate Bliss Independence synergy score for a drug combination. Model: E_expected = E_a + E_b ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugSynergy_calculate_bliss(
    operation: str,
    effect_a: float,
    effect_b: float,
    effect_combination: float,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate Bliss Independence synergy score for a drug combination. Model: E_expected = E_a + E_b ...

    Parameters
    ----------
    operation : str
        Operation type
    effect_a : float
        Fractional inhibition of drug A alone (0=no effect, 1=complete inhibition)
    effect_b : float
        Fractional inhibition of drug B alone (0=no effect, 1=complete inhibition)
    effect_combination : float
        Observed fractional inhibition of the drug combination
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
    _args = {k: v for k, v in {
        "operation": operation,
                "effect_a": effect_a,
                "effect_b": effect_b,
                "effect_combination": effect_combination
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DrugSynergy_calculate_bliss",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["DrugSynergy_calculate_bliss"]
