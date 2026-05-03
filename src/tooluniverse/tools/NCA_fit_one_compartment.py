"""
NCA_fit_one_compartment

Fit a one-compartment IV bolus pharmacokinetic model (C(t) = C0 × exp(-k_el × t)) to plasma conce...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCA_fit_one_compartment(
    times: list[Any],
    concentrations: list[Any],
    dose: Optional[float | Any] = None,
    dose_unit: Optional[str | Any] = None,
    conc_unit: Optional[str | Any] = None,
    time_unit: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fit a one-compartment IV bolus pharmacokinetic model (C(t) = C0 × exp(-k_el × t)) to plasma conce...

    Parameters
    ----------
    times : list[Any]
        Time points after IV administration. Example: [0, 0.5, 1, 2, 4, 8, 12, 24].
    concentrations : list[Any]
        Plasma concentrations at each time point. Example: [500, 380, 290, 170, 60, 8...
    dose : float | Any
        Administered IV dose. Required to calculate Vd and CL.
    dose_unit : str | Any
        Unit of dose (default: 'mg').
    conc_unit : str | Any
        Unit of concentration (default: 'ng/mL').
    time_unit : str | Any
        Unit of time (default: 'h').
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
            "times": times,
            "concentrations": concentrations,
            "dose": dose,
            "dose_unit": dose_unit,
            "conc_unit": conc_unit,
            "time_unit": time_unit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCA_fit_one_compartment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCA_fit_one_compartment"]
