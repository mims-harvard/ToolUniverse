"""
ClinicalTrials_get_study

Get full details for a specific clinical trial by NCT ID from ClinicalTrials.gov. Returns compreh...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrials_get_study(
    nct_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get full details for a specific clinical trial by NCT ID from ClinicalTrials.gov. Returns compreh...

    Parameters
    ----------
    nct_id : str
        NCT (National Clinical Trial) identifier (e.g., 'NCT04280705', 'NCT02142712')...
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

    return get_shared_client().run_one_function(
        {"name": "ClinicalTrials_get_study", "arguments": {"nct_id": nct_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrials_get_study"]
