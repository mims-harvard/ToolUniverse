"""
extract_clinical_trial_adverse_events

Extracts detailed adverse event results from clinicaltrials.gov, using their NCT IDs.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def extract_clinical_trial_adverse_events(
    nct_ids: list[str],
    organ_systems: Optional[list[str]] = None,
    adverse_event_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Extracts detailed adverse event results from clinicaltrials.gov, using their NCT IDs.

    Parameters
    ----------
    nct_ids : list[str]
        List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).
    organ_systems : list[str]
        List of organs or organ systems to filter adverse events (see enum for exact ...
    adverse_event_type : str
        Type of adverse events to extract. Options are 'serious' (serious adverse eve...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "nct_ids": nct_ids,
            "organ_systems": organ_systems,
            "adverse_event_type": adverse_event_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "extract_clinical_trial_adverse_events",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["extract_clinical_trial_adverse_events"]
