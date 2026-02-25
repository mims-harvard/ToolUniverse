"""
DrugSynergy_calculate_zip

Calculate ZIP (Zero Interaction Potency) delta synergy score from a full dose-response matrix. Fi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugSynergy_calculate_zip(
    operation: str,
    doses_a: list[Any],
    doses_b: list[Any],
    viability_matrix: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate ZIP (Zero Interaction Potency) delta synergy score from a full dose-response matrix. Fi...

    Parameters
    ----------
    operation : str
        Operation type
    doses_a : list[Any]
        Concentration values for drug A (e.g., [0.01, 0.1, 1, 10])
    doses_b : list[Any]
        Concentration values for drug B (e.g., [0.01, 0.1, 1, 10])
    viability_matrix : list[Any]
        2D matrix of cell viability percentages (0-100). Rows = doses_a, Columns = do...
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
            "name": "DrugSynergy_calculate_zip",
            "arguments": {
                "operation": operation,
                "doses_a": doses_a,
                "doses_b": doses_b,
                "viability_matrix": viability_matrix,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugSynergy_calculate_zip"]
