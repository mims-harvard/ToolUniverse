"""
NCA_compute_parameters

Perform Non-Compartmental Analysis (NCA) on time-concentration pharmacokinetic data. Computes key...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCA_compute_parameters(
    times: list[Any],
    concentrations: list[Any],
    dose: Optional[float | Any] = None,
    route: Optional[str | Any] = None,
    dose_unit: Optional[str | Any] = None,
    conc_unit: Optional[str | Any] = None,
    time_unit: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform Non-Compartmental Analysis (NCA) on time-concentration pharmacokinetic data. Computes key...

    Parameters
    ----------
    times : list[Any]
        Time points in consistent units (hours recommended). Example: [0, 0.25, 0.5, ...
    concentrations : list[Any]
        Plasma concentrations at each time point (same length as times). Example: [0,...
    dose : float | Any
        Administered dose (optional). Required to calculate CL and Vd. Example: 100 (...
    route : str | Any
        Route of administration: 'iv' (default) or 'po'. Affects Vd calculation formula.
    dose_unit : str | Any
        Unit of dose (default: 'mg'). Examples: 'mg', 'ug', 'nmol'.
    conc_unit : str | Any
        Unit of concentration (default: 'ng/mL'). Examples: 'ng/mL', 'ug/L', 'nM'.
    time_unit : str | Any
        Unit of time (default: 'h'). Examples: 'h', 'min', 'd'.
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

    return get_shared_client().run_one_function(
        {
            "name": "NCA_compute_parameters",
            "arguments": {
                "times": times,
                "concentrations": concentrations,
                "dose": dose,
                "route": route,
                "dose_unit": dose_unit,
                "conc_unit": conc_unit,
                "time_unit": time_unit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCA_compute_parameters"]
