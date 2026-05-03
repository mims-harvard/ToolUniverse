"""
get_clinical_trial_descriptions

Retrieves detailed identification information for trials, including titles, phases, and descripti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_clinical_trial_descriptions(
    nct_ids: list[str],
    description_type: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Retrieves detailed identification information for trials, including titles, phases, and descripti...

    Parameters
    ----------
    nct_ids : list[str]
        List of NCT IDs of the clinical trials (e.g., ['NCT04852770', 'NCT01728545']).
    description_type : str
        Type of information to retrieve. Options are 'brief' for brief descriptions o...
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
        for k, v in {"nct_ids": nct_ids, "description_type": description_type}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "get_clinical_trial_descriptions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_clinical_trial_descriptions"]
