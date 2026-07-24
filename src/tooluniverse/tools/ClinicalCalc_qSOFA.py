"""
ClinicalCalc_qSOFA

qSOFA (quick SOFA): bedside identification of patients with suspected infection at higher risk of...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_qSOFA(
    high_resp_rate: Optional[bool] = None,
    altered_mentation: Optional[bool] = None,
    low_sbp: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    qSOFA (quick SOFA): bedside identification of patients with suspected infection at higher risk of...

    Parameters
    ----------
    high_resp_rate : bool
        Respiratory rate >=22/min
    altered_mentation : bool
        Altered mental status (GCS <15)
    low_sbp : bool
        Systolic blood pressure <=100 mmHg
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
            "high_resp_rate": high_resp_rate,
            "altered_mentation": altered_mentation,
            "low_sbp": low_sbp,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_qSOFA",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_qSOFA"]
