"""
FAERS_count_additive_reaction_outcomes

Determine reaction outcome counts (e.g., recovered, resolving, fatal) across medicinal products. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_additive_reaction_outcomes(
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
    Determine reaction outcome counts (e.g., recovered, resolving, fatal) across medicinal products. ...

    Parameters
    ----------
    medicinalproducts : list[str]
        Array of medicinal product names.
    patientsex : str

    patientagegroup : str

    occurcountry : str

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
            "name": "FAERS_count_additive_reaction_outcomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_additive_reaction_outcomes"]
