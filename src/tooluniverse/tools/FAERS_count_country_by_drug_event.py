"""
FAERS_count_country_by_drug_event

Count the number of adverse event reports per country of occurrence. Only medicinalproduct is req...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_country_by_drug_event(
    medicinalproduct: str,
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    serious: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Count the number of adverse event reports per country of occurrence. Only medicinalproduct is req...

    Parameters
    ----------
    medicinalproduct : str
        Drug name.
    patientsex : str
        Optional: Filter by patient sex. Omit this parameter if you don't want to fil...
    patientagegroup : str
        Optional: Filter by patient age group. Omit this parameter if you don't want ...
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
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "medicinalproduct": medicinalproduct,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "serious": serious,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_country_by_drug_event",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_country_by_drug_event"]
