"""
ClinicalCalc_MELD_Na

MELD-Na score (UNOS/OPTN 2016): 90-day mortality risk in chronic liver disease and liver transpla...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_MELD_Na(
    creatinine: float,
    bilirubin: float,
    inr: float,
    sodium: float,
    dialysis: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    MELD-Na score (UNOS/OPTN 2016): 90-day mortality risk in chronic liver disease and liver transpla...

    Parameters
    ----------
    creatinine : float
        Serum creatinine in mg/dL (bounded 1.0-4.0; set to 4.0 if on dialysis)
    bilirubin : float
        Total bilirubin in mg/dL (lower-bounded at 1.0)
    inr : float
        INR (lower-bounded at 1.0)
    sodium : float
        Serum sodium in mmol/L (bounded 125-137)
    dialysis : bool
        Two or more dialysis sessions in the past week (forces creatinine to 4.0)
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
            "bilirubin": bilirubin,
            "inr": inr,
            "sodium": sodium,
            "dialysis": dialysis,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_MELD_Na",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_MELD_Na"]
