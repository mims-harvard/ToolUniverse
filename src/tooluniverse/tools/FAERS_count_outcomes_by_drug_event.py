"""
FAERS_count_outcomes_by_drug_event

Count the outcome of adverse reactions (recovered, recovering, fatal, unresolved). Only medicinal...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_outcomes_by_drug_event(
    medicinalproduct: str,
    patientsex: Optional[str] = None,
    patientagegroup: Optional[str] = None,
    occurcountry: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Count the outcome of adverse reactions (recovered, recovering, fatal, unresolved). Only medicinal...

    Parameters
    ----------
    medicinalproduct : str
        Drug name.
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
            "medicinalproduct": medicinalproduct,
            "patientsex": patientsex,
            "patientagegroup": patientagegroup,
            "occurcountry": occurcountry,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_outcomes_by_drug_event",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_outcomes_by_drug_event"]
