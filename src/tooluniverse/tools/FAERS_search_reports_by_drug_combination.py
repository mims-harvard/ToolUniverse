"""
FAERS_search_reports_by_drug_combination

Search and retrieve detailed adverse event reports involving multiple drugs (drug interactions). ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_search_reports_by_drug_combination(
    medicinalproducts: list[str],
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    serious: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search and retrieve detailed adverse event reports involving multiple drugs (drug interactions). ...

    Parameters
    ----------
    medicinalproducts : list[str]
        List of at least 2 drug names (required). Reports will include cases where al...
    limit : int
        Maximum number of reports to return. Must be between 1 and 100.
    skip : int
        Number of reports to skip for pagination. Must be non-negative.
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
            "medicinalproducts": medicinalproducts,
            "limit": limit,
            "skip": skip,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "serious": serious,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_search_reports_by_drug_combination",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_search_reports_by_drug_combination"]
