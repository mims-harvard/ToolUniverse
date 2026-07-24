"""
ClinicalCalc_Child_Pugh

Child-Pugh score and class (A/B/C): severity of chronic liver disease / cirrhosis and surgical ri...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_Child_Pugh(
    bilirubin: float,
    albumin: float,
    inr: float,
    ascites: Optional[str] = "none",
    encephalopathy: Optional[str] = "none",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Child-Pugh score and class (A/B/C): severity of chronic liver disease / cirrhosis and surgical ri...

    Parameters
    ----------
    bilirubin : float
        Total bilirubin in mg/dL
    albumin : float
        Serum albumin in g/dL
    inr : float
        INR (prothrombin time ratio)
    ascites : str
        Ascites severity. Accepted: 'none'/'absent' (1 pt), 'mild'/'slight' (2 pts), ...
    encephalopathy : str
        Hepatic encephalopathy grade. Accepted: 'none'/'absent' (1 pt), 'grade1-2' (2...
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
            "bilirubin": bilirubin,
            "albumin": albumin,
            "inr": inr,
            "ascites": ascites,
            "encephalopathy": encephalopathy,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_Child_Pugh",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_Child_Pugh"]
