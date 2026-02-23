"""
NASA_DONKI_get_coronal_mass_ejections

Search NASA DONKI (Database Of Notifications, Knowledge, Information) for Coronal Mass Ejection (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASA_DONKI_get_coronal_mass_ejections(
    startDate: Optional[str | Any] = None,
    endDate: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search NASA DONKI (Database Of Notifications, Knowledge, Information) for Coronal Mass Ejection (...

    Parameters
    ----------
    startDate : str | Any
        Start date in YYYY-MM-DD format (e.g., '2024-01-01'). Defaults to 30 days bef...
    endDate : str | Any
        End date in YYYY-MM-DD format (e.g., '2024-01-31'). Defaults to today.
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
        {
            "name": "NASA_DONKI_get_coronal_mass_ejections",
            "arguments": {"startDate": startDate, "endDate": endDate},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASA_DONKI_get_coronal_mass_ejections"]
