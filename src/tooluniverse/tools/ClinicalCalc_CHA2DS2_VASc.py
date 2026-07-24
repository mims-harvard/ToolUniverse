"""
ClinicalCalc_CHA2DS2_VASc

CHA2DS2-VASc score: stroke risk in non-valvular atrial fibrillation, used to decide oral anticoag...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_CHA2DS2_VASc(
    age: float,
    chf: Optional[bool] = None,
    hypertension: Optional[bool] = None,
    diabetes: Optional[bool] = None,
    stroke_history: Optional[bool] = None,
    vascular_disease: Optional[bool] = None,
    female: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    CHA2DS2-VASc score: stroke risk in non-valvular atrial fibrillation, used to decide oral anticoag...

    Parameters
    ----------
    age : float
        Age in years
    chf : bool
        Congestive heart failure / LV dysfunction
    hypertension : bool
        History of hypertension
    diabetes : bool
        Diabetes mellitus
    stroke_history : bool
        Prior stroke, TIA, or thromboembolism (2 points)
    vascular_disease : bool
        Vascular disease (prior MI, PAD, aortic plaque)
    female : bool
        Female sex
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
            "chf": chf,
            "hypertension": hypertension,
            "diabetes": diabetes,
            "stroke_history": stroke_history,
            "vascular_disease": vascular_disease,
            "female": female,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_CHA2DS2_VASc",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_CHA2DS2_VASc"]
