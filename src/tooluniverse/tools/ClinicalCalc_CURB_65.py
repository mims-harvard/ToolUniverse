"""
ClinicalCalc_CURB_65

CURB-65 score: community-acquired pneumonia severity and disposition (outpatient vs inpatient vs ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_CURB_65(
    age: float,
    confusion: Optional[bool] = None,
    elevated_urea: Optional[bool] = None,
    high_resp_rate: Optional[bool] = None,
    low_bp: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    CURB-65 score: community-acquired pneumonia severity and disposition (outpatient vs inpatient vs ...

    Parameters
    ----------
    age : float
        Age in years (>=65 scores 1)
    confusion : bool
        New-onset confusion / altered mental status
    elevated_urea : bool
        Blood urea nitrogen >7 mmol/L (>19 mg/dL BUN)
    high_resp_rate : bool
        Respiratory rate >=30/min
    low_bp : bool
        SBP <90 mmHg or DBP <=60 mmHg
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
            "confusion": confusion,
            "elevated_urea": elevated_urea,
            "high_resp_rate": high_resp_rate,
            "low_bp": low_bp,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_CURB_65",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_CURB_65"]
