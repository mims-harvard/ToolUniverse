"""
FAERS_filter_serious_events

Filter for serious adverse events (death, hospitalization, disability, life-threatening). Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAERS_filter_serious_events(
    operation: Optional[str] = None,
    drug_name: Optional[str] = None,
    seriousness_type: Optional[str] = "all",
    drug: Optional[str] = None,
    event_type: Optional[str] = None,
    adverse_event: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Filter for serious adverse events (death, hospitalization, disability, life-threatening). Returns...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    drug_name : str
        Generic drug name
    seriousness_type : str
        Type of serious event to filter
    drug : str
        Alias for drug_name. Generic drug name.
    event_type : str
        Alias for seriousness_type. Type of serious event (e.g., hospitalization, dea...
    adverse_event : str
        Specific adverse event MedDRA term to filter within serious events (e.g., MYO...
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
            "drug_name": drug_name,
            "seriousness_type": seriousness_type,
            "drug": drug,
            "event_type": event_type,
            "adverse_event": adverse_event,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FAERS_filter_serious_events",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAERS_filter_serious_events"]
