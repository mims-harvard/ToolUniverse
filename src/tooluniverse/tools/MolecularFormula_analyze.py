"""
MolecularFormula_analyze

Analyze a molecular formula to calculate molar mass, degrees of unsaturation (DoU), and elemental...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MolecularFormula_analyze(
    operation: str,
    formula: Optional[str | Any] = None,
    sample_g: Optional[float | Any] = None,
    CO2_g: Optional[float | Any] = None,
    H2O_g: Optional[float | Any] = None,
    N2_g: Optional[float | Any] = 0.0,
    molar_mass: Optional[float | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Analyze a molecular formula to calculate molar mass, degrees of unsaturation (DoU), and elemental...

    Parameters
    ----------
    operation : str
        Operation: 'analyze_formula' to analyze a known formula, or 'combustion_analy...
    formula : str | Any
        Molecular formula string (e.g., 'C6H12O6', 'C8H9NO2'). Required for analyze_f...
    sample_g : float | Any
        Mass of sample burned in grams. Required for combustion_analysis mode.
    CO2_g : float | Any
        Mass of CO2 collected in grams. Required for combustion_analysis mode.
    H2O_g : float | Any
        Mass of H2O collected in grams. Required for combustion_analysis mode.
    N2_g : float | Any
        Mass of N2 collected in grams (optional, default 0).
    molar_mass : float | Any
        Known molar mass in g/mol to determine molecular formula from empirical formu...
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
            "formula": formula,
            "sample_g": sample_g,
            "CO2_g": CO2_g,
            "H2O_g": H2O_g,
            "N2_g": N2_g,
            "molar_mass": molar_mass,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MolecularFormula_analyze",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MolecularFormula_analyze"]
