"""
FAERS_calculate_disproportionality

Calculate statistical disproportionality measures (ROR, PRR, IC) with 95% CI for drug-event pairs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_calculate_disproportionality(
    operation: Optional[str] = None,
    drug_name: Optional[str] = None,
    adverse_event: Optional[str] = None,
    reaction: Optional[str] = None,
    drug: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Calculate statistical disproportionality measures (ROR, PRR, IC) with 95% CI for drug-event pairs...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    drug_name : str
        Generic drug name (e.g., 'IBUPROFEN', 'ATORVASTATIN')
    adverse_event : str
        MedDRA Preferred Term (e.g., 'Hepatotoxicity', 'Myopathy'). Use exact MedDRA ...
    reaction : str
        Alias for adverse_event. MedDRA Preferred Term for the adverse drug reaction.
    drug : str
        Alias for drug_name. Generic drug name.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "drug_name": drug_name,
            "adverse_event": adverse_event,
            "reaction": reaction,
            "drug": drug,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_calculate_disproportionality",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_calculate_disproportionality"]
