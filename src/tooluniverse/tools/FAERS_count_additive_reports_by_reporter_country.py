"""
FAERS_count_additive_reports_by_reporter_country

Aggregate adverse event reports by primary reporter country across medicinal products. Only medic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_additive_reports_by_reporter_country(
    medicinalproducts: list[str],
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    serious: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Aggregate adverse event reports by primary reporter country across medicinal products. Only medic...

    Parameters
    ----------
    medicinalproducts : list[str]
        Array of medicinal product names.
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
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "serious": serious,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_additive_reports_by_reporter_country",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_additive_reports_by_reporter_country"]
