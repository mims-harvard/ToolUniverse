"""
FAERS_count_patient_age_distribution

Analyze the age distribution of patients experiencing adverse events for a specific drug. Only me...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_count_patient_age_distribution(
    medicinalproduct: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Analyze the age distribution of patients experiencing adverse events for a specific drug. Only me...

    Parameters
    ----------
    medicinalproduct : str
        Drug name.
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
        k: v for k, v in {"medicinalproduct": medicinalproduct}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_count_patient_age_distribution",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_count_patient_age_distribution"]
