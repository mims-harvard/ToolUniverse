"""
DrugSynergy_calculate_ci

Calculate Chou-Talalay Combination Index (CI) for drug synergy quantification. CI is derived from...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugSynergy_calculate_ci(
    operation: str,
    doses_a_single: list[Any],
    effects_a_single: list[Any],
    doses_b_single: list[Any],
    effects_b_single: list[Any],
    dose_a_combo: float,
    dose_b_combo: float,
    effect_combo: float,
    assumption: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate Chou-Talalay Combination Index (CI) for drug synergy quantification. CI is derived from...

    Parameters
    ----------
    operation : str
        Operation type
    doses_a_single : list[Any]
        Concentration values for drug A single-agent dose-response (e.g., [0.01, 0.1,...
    effects_a_single : list[Any]
        Fractional inhibition of drug A alone at each dose (0-1 scale)
    doses_b_single : list[Any]
        Concentration values for drug B single-agent dose-response
    effects_b_single : list[Any]
        Fractional inhibition of drug B alone at each dose (0-1 scale)
    dose_a_combo : float
        Dose of drug A used in the combination
    dose_b_combo : float
        Dose of drug B used in the combination
    effect_combo : float
        Observed fractional inhibition of the combination (0-1 scale, must be between...
    assumption : str
        Whether drugs have similar (mutually_exclusive) or different (mutually_non_ex...
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

    return get_shared_client().run_one_function(
        {
            "name": "DrugSynergy_calculate_ci",
            "arguments": {
                "operation": operation,
                "doses_a_single": doses_a_single,
                "effects_a_single": effects_a_single,
                "doses_b_single": doses_b_single,
                "effects_b_single": effects_b_single,
                "dose_a_combo": dose_a_combo,
                "dose_b_combo": dose_b_combo,
                "effect_combo": effect_combo,
                "assumption": assumption,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugSynergy_calculate_ci"]
