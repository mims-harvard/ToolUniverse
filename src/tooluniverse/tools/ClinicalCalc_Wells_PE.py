"""
ClinicalCalc_Wells_PE

Wells score for pulmonary embolism (PE) pretest probability. Weighted score giving three-tier (lo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_Wells_PE(
    clinical_dvt: Optional[bool] = None,
    pe_most_likely: Optional[bool] = None,
    tachycardia: Optional[bool] = None,
    immobilization: Optional[bool] = None,
    previous_vte: Optional[bool] = None,
    hemoptysis: Optional[bool] = None,
    malignancy: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Wells score for pulmonary embolism (PE) pretest probability. Weighted score giving three-tier (lo...

    Parameters
    ----------
    clinical_dvt : bool
        Clinical signs/symptoms of DVT (3 points)
    pe_most_likely : bool
        PE is the most likely diagnosis (3 points)
    tachycardia : bool
        Heart rate >100 bpm (1.5)
    immobilization : bool
        Immobilization >=3 days or surgery within 4 weeks (1.5)
    previous_vte : bool
        Previous DVT or PE (1.5)
    hemoptysis : bool
        Hemoptysis (1)
    malignancy : bool
        Malignancy treated within 6 months or palliative (1)
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
            "clinical_dvt": clinical_dvt,
            "pe_most_likely": pe_most_likely,
            "tachycardia": tachycardia,
            "immobilization": immobilization,
            "previous_vte": previous_vte,
            "hemoptysis": hemoptysis,
            "malignancy": malignancy,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_Wells_PE",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_Wells_PE"]
