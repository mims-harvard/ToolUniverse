"""
ClinicalCalc_HAS_BLED

HAS-BLED score: 1-year major bleeding risk in patients with atrial fibrillation on anticoagulatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_HAS_BLED(
    age: float,
    hypertension: Optional[bool] = None,
    renal_disease: Optional[bool] = None,
    liver_disease: Optional[bool] = None,
    stroke_history: Optional[bool] = None,
    bleeding_history: Optional[bool] = None,
    labile_inr: Optional[bool] = None,
    drugs: Optional[bool] = None,
    alcohol: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    HAS-BLED score: 1-year major bleeding risk in patients with atrial fibrillation on anticoagulatio...

    Parameters
    ----------
    age : float
        Age in years (>65 scores 1 point)
    hypertension : bool
        Uncontrolled hypertension (SBP >160)
    renal_disease : bool
        Abnormal renal function (dialysis, transplant, Cr >2.26 mg/dL)
    liver_disease : bool
        Abnormal liver function (cirrhosis, bilirubin >2x or AST/ALT >3x normal)
    stroke_history : bool
        Prior stroke
    bleeding_history : bool
        Prior major bleeding or predisposition
    labile_inr : bool
        Labile INR (unstable/high, TTR <60%)
    drugs : bool
        Concomitant antiplatelet or NSAID use
    alcohol : bool
        Alcohol >=8 drinks/week
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
            "hypertension": hypertension,
            "renal_disease": renal_disease,
            "liver_disease": liver_disease,
            "stroke_history": stroke_history,
            "bleeding_history": bleeding_history,
            "labile_inr": labile_inr,
            "drugs": drugs,
            "alcohol": alcohol,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_HAS_BLED",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_HAS_BLED"]
