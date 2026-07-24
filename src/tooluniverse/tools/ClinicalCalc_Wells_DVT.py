"""
ClinicalCalc_Wells_DVT

Wells score for deep vein thrombosis (DVT) pretest probability. Sum of clinical features (minus 2...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalCalc_Wells_DVT(
    active_cancer: Optional[bool] = None,
    immobilization: Optional[bool] = None,
    recent_surgery: Optional[bool] = None,
    localized_tenderness: Optional[bool] = None,
    leg_swollen: Optional[bool] = None,
    calf_swelling: Optional[bool] = None,
    pitting_edema: Optional[bool] = None,
    collateral_veins: Optional[bool] = None,
    previous_dvt: Optional[bool] = None,
    alternative_diagnosis: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Wells score for deep vein thrombosis (DVT) pretest probability. Sum of clinical features (minus 2...

    Parameters
    ----------
    active_cancer : bool
        Active cancer (treatment within 6 months or palliative)
    immobilization : bool
        Paralysis, paresis, or recent lower-limb immobilization
    recent_surgery : bool
        Recently bedridden >=3 days or major surgery within 12 weeks
    localized_tenderness : bool
        Localized tenderness along deep venous system
    leg_swollen : bool
        Entire leg swollen
    calf_swelling : bool
        Calf swelling >3 cm vs asymptomatic side
    pitting_edema : bool
        Pitting edema confined to symptomatic leg
    collateral_veins : bool
        Collateral superficial (non-varicose) veins
    previous_dvt : bool
        Previously documented DVT
    alternative_diagnosis : bool
        Alternative diagnosis at least as likely as DVT (subtracts 2)
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
            "active_cancer": active_cancer,
            "immobilization": immobilization,
            "recent_surgery": recent_surgery,
            "localized_tenderness": localized_tenderness,
            "leg_swollen": leg_swollen,
            "calf_swelling": calf_swelling,
            "pitting_edema": pitting_edema,
            "collateral_veins": collateral_veins,
            "previous_dvt": previous_dvt,
            "alternative_diagnosis": alternative_diagnosis,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinicalCalc_Wells_DVT",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalCalc_Wells_DVT"]
