"""
NCA_calculate_bioavailability

Calculate absolute oral bioavailability (F) from paired IV and PO pharmacokinetic study AUC value...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCA_calculate_bioavailability(
    auc_po: float,
    dose_po: float,
    auc_iv: float,
    dose_iv: float,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate absolute oral bioavailability (F) from paired IV and PO pharmacokinetic study AUC value...

    Parameters
    ----------
    auc_po : float
        AUC from the oral (PO) arm. Must be in same units as auc_iv. Example: 2400 (n...
    dose_po : float
        Dose administered orally. Must be in same units as dose_iv. Example: 100 (mg).
    auc_iv : float
        AUC from the intravenous (IV) arm. Example: 3500 (ng/mL·h).
    dose_iv : float
        Dose administered intravenously. Example: 50 (mg).
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

    return get_shared_client().run_one_function(
        {
            "name": "NCA_calculate_bioavailability",
            "arguments": {
                "auc_po": auc_po,
                "dose_po": dose_po,
                "auc_iv": auc_iv,
                "dose_iv": dose_iv,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCA_calculate_bioavailability"]
