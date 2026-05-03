"""
EnzymeKinetics_calculate

Calculate enzyme kinetic parameters from experimental data. Supports: (1) Michaelis-Menten Km/Vma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnzymeKinetics_calculate(
    operation: str,
    substrate_concs: list[Any],
    velocities: Optional[list[Any] | Any] = None,
    velocities_no_inhibitor: Optional[list[Any] | Any] = None,
    velocities_with_inhibitor: Optional[list[Any] | Any] = None,
    inhibitor_conc: Optional[float | Any] = None,
    inhibition_type: Optional[str | Any] = "competitive",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate enzyme kinetic parameters from experimental data. Supports: (1) Michaelis-Menten Km/Vma...

    Parameters
    ----------
    operation : str
        Calculation type: 'michaelis_menten' for Km/Vmax, 'hill' for Hill coefficient...
    substrate_concs : list[Any]
        Substrate concentrations (at least 3 values). Must be positive.
    velocities : list[Any] | Any
        Measured velocities corresponding to substrate_concs. Required for michaelis_...
    velocities_no_inhibitor : list[Any] | Any
        Velocities without inhibitor (required for inhibition mode).
    velocities_with_inhibitor : list[Any] | Any
        Velocities with inhibitor (required for inhibition mode).
    inhibitor_conc : float | Any
        Inhibitor concentration (required for inhibition mode).
    inhibition_type : str | Any
        Type of inhibition (default: competitive).
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
            "substrate_concs": substrate_concs,
            "velocities": velocities,
            "velocities_no_inhibitor": velocities_no_inhibitor,
            "velocities_with_inhibitor": velocities_with_inhibitor,
            "inhibitor_conc": inhibitor_conc,
            "inhibition_type": inhibition_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnzymeKinetics_calculate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnzymeKinetics_calculate"]
