"""
FAERS_count_additive_seriousness_classification

Quantify serious vs non-serious classifications across medicinal products. Only medicinalproducts...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_additive_seriousness_classification(
    medicinalproducts: list[str],
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    occurcountry: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Quantify serious vs non-serious classifications across medicinal products. Only medicinalproducts...

    Parameters
    ----------
    medicinalproducts : list[str]
        Array of medicinal product names.
    patientsex : str
        Optional: Filter by patient sex. Omit this parameter if you don't want to fil...
    patientagegroup : str
        Optional: Filter by patient age group. Omit this parameter if you don't want ...
    occurcountry : str
        Optional: Filter by country where event occurred (ISO2 code, e.g., 'US', 'GB'...
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
            "medicinalproducts": medicinalproducts,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "occurcountry": occurcountry,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_additive_seriousness_classification",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_additive_seriousness_classification"]
