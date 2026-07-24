"""
ClinicalCalc_ASCVD_risk

10-year atherosclerotic cardiovascular disease (ASCVD) risk by the 2013 ACC/AHA Pooled Cohort Equ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_ASCVD_risk(
    age: float,
    total_cholesterol: float,
    hdl_cholesterol: float,
    systolic_bp: float,
    bp_treated: Optional[bool] = None,
    smoker: Optional[bool] = None,
    diabetes: Optional[bool] = None,
    female: Optional[bool] = None,
    race: Optional[str] = "white",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    10-year atherosclerotic cardiovascular disease (ASCVD) risk by the 2013 ACC/AHA Pooled Cohort Equ...

    Parameters
    ----------
    age : float
        Age in years (40-79)
    total_cholesterol : float
        Total cholesterol in mg/dL
    hdl_cholesterol : float
        HDL cholesterol in mg/dL
    systolic_bp : float
        Systolic blood pressure in mmHg
    bp_treated : bool
        Currently on blood-pressure-lowering medication
    smoker : bool
        Current smoker
    diabetes : bool
        Diabetes mellitus
    female : bool
        Female sex
    race : str
        'white' (or other) vs 'black'/'African American'; affects the coefficient set
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
            "age": age,
            "total_cholesterol": total_cholesterol,
            "hdl_cholesterol": hdl_cholesterol,
            "systolic_bp": systolic_bp,
            "bp_treated": bp_treated,
            "smoker": smoker,
            "diabetes": diabetes,
            "female": female,
            "race": race,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_ASCVD_risk",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_ASCVD_risk"]
