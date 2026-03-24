"""
FAERS_compare_drugs

Compare safety signals for two drugs with the same adverse event. Returns ROR/PRR/IC for both dru...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_compare_drugs(
    operation: Optional[str] = None,
    drug1: Optional[str] = None,
    drug2: Optional[str] = None,
    adverse_event: Optional[str] = None,
    reaction: Optional[str] = None,
    drugs: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compare safety signals for two drugs with the same adverse event. Returns ROR/PRR/IC for both dru...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    drug1 : str
        First drug name (generic)
    drug2 : str
        Second drug name (generic)
    adverse_event : str
        MedDRA Preferred Term to compare. Use exact MedDRA Preferred Term capitalizat...
    reaction : str
        Alias for adverse_event. MedDRA Preferred Term for the adverse drug reaction.
    drugs : list[str]
        Alias for drug1/drug2. List of two drug names to compare, e.g., ["tofacitinib...
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
            "drug1": drug1,
            "drug2": drug2,
            "adverse_event": adverse_event,
            "reaction": reaction,
            "drugs": drugs,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_compare_drugs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_compare_drugs"]
