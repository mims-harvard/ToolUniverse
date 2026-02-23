"""
ClinicalTrials_get_database_stats

Get aggregate statistics about the ClinicalTrials.gov database, including total number of registe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinicalTrials_get_database_stats(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get aggregate statistics about the ClinicalTrials.gov database, including total number of registe...

    Parameters
    ----------
    No parameters
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
        {"name": "ClinicalTrials_get_database_stats", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinicalTrials_get_database_stats"]
