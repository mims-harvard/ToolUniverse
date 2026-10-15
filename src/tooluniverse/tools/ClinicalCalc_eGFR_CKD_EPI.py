"""
ClinicalCalc_eGFR_CKD_EPI

Estimated glomerular filtration rate (eGFR) by the CKD-EPI 2021 creatinine equation (race-free, I...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_eGFR_CKD_EPI(
    creatinine: float,
    age: float,
    female: Optional[bool] = None,
    sex: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Estimated glomerular filtration rate (eGFR) by the CKD-EPI 2021 creatinine equation (race-free, I...

    Parameters
    ----------
    creatinine : float
        Serum creatinine in mg/dL. Must be greater than 0; a value below 0.2 is under...
    age : float
        Age in years. Must be greater than 0. CKD-EPI 2021 was derived in adults; an ...
    female : bool
        Female sex (legacy boolean; equivalent to sex='female'). If both 'female' and...
    sex : str
        Biological sex: 'female'/'f' or 'male'/'m' (case-insensitive). Preferred over...
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
            "creatinine": creatinine,
            "age": age,
            "female": female,
            "sex": sex,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_eGFR_CKD_EPI",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_eGFR_CKD_EPI"]
