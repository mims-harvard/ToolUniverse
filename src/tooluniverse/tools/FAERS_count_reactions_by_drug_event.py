"""
FAERS_count_reactions_by_drug_event

Count the number of adverse reactions reported for a given drug. Only medicinalproduct is require...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_reactions_by_drug_event(
    medicinalproduct: str,
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    occurcountry: Optional[str] = None,
    serious: Optional[str] = None,
    seriousnessdeath: Optional[str] = None,
    reactionmeddraverse: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Count the number of adverse reactions reported for a given drug. Only medicinalproduct is require...

    Parameters
    ----------
    medicinalproduct : str
        Drug name.
    patientsex : str
        Optional: Filter by patient sex. Omit this parameter if you don't want to fil...
    patientagegroup : str
        Optional: Filter by patient age group. Omit this parameter if you don't want ...
    occurcountry : str
        Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'...
    serious : str
        Optional: Filter by event seriousness. Omit this parameter if you don't want ...
    seriousnessdeath : str
        Optional: Pass 'Yes' to filter for reports where death was an outcome. Omit t...
    reactionmeddraverse : str
        Optional: Filter by MedDRA reaction term (Lowest Level Term). When omitted, r...
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
            "medicinalproduct": medicinalproduct,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "occurcountry": occurcountry,
            "serious": serious,
            "seriousnessdeath": seriousnessdeath,
            "reactionmeddraverse": reactionmeddraverse,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_reactions_by_drug_event",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_reactions_by_drug_event"]
