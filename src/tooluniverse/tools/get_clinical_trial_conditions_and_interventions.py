"""
get_clinical_trial_conditions_and_interventions

Retrieves the list of conditions or diseases and the interventions and arm groups that the clinic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_clinical_trial_conditions_and_interventions(
    nct_ids: list[str],
    condition_and_intervention: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Retrieves the list of conditions or diseases and the interventions and arm groups that the clinic...

    Parameters
    ----------
    nct_ids : list[str]
        List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).
    condition_and_intervention : str
        Unused filter parameter, kept for backward compatibility. Can be omitted or s...
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
            "nct_ids": nct_ids,
            "condition_and_intervention": condition_and_intervention,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "get_clinical_trial_conditions_and_interventions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_clinical_trial_conditions_and_interventions"]
