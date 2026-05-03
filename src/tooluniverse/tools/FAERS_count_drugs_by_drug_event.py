"""
FAERS_count_drugs_by_drug_event

Count the number of different drugs involved in FDA adverse event reports. All filters (patientse...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_drugs_by_drug_event(
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    occurcountry: Optional[str] = None,
    serious: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Count the number of different drugs involved in FDA adverse event reports. All filters (patientse...

    Parameters
    ----------
    patientsex : str
        Optional: Filter by patient sex. Omit this parameter if you don't want to fil...
    patientagegroup : str
        Optional: Filter by patient age group. Omit this parameter if you don't want ...
    occurcountry : str
        Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'...
    serious : str
        Optional: Filter by event seriousness. Omit this parameter if you don't want ...
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
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "occurcountry": occurcountry,
            "serious": serious,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_drugs_by_drug_event",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_drugs_by_drug_event"]
